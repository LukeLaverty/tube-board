"""
Paths, defaults and config loading.
"""

import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

from .selection import validate

CONFIG_NAME = "config.toml"
ENV_NAME = ".env"
# The repository root.
CHECKOUT = Path(__file__).resolve().parent.parent


def _search_path(name: str) -> list[Path]:
    """
    Where to look for a config or env file, in order. The checkout is on the
    list so cron jobs, which run from $HOME, still find it.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME")
    home = Path(xdg) if xdg else Path.home() / ".config"
    return [
        Path.cwd() / name,
        CHECKOUT / name,
        home / "tube-board" / name,
        Path("/etc/tube-board") / name,
    ]


def find_config(name: str = CONFIG_NAME) -> Path | None:
    """
    The first config file that exists, or None.
    """
    return next((path for path in _search_path(name) if path.exists()), None)


SHOW_LINE_NAMES = ("auto", "always", "never")


@dataclass
class Station:
    """
    The departure board's station and filters.
    """

    name: str = "King's Cross St. Pancras"
    id: str = "940GZZLUKSX"
    lines: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    show_line_names: str = "auto"
    max_rows: int = 3


@dataclass
class Display:
    """
    The LED panel, and how often the status board interrupts it.
    """

    width: int = 256
    height: int = 64
    scale: int = 6
    fps: int = 30
    status_every: float = 60.0
    status_follows_schedule: bool = False


@dataclass
class Status:
    """
    Which lines the status board shows. Each schedule rule is a table with
    `days` and `lines`; see `selection.py`.
    """

    lines: list[str] = field(default_factory=list)
    schedule: list[dict] = field(default_factory=list)


@dataclass
class StatusDisplay:
    width: int = 800
    height: int = 480


@dataclass
class Refresh:
    """
    API polling intervals, in seconds.
    """

    arrivals_seconds: float = 10.0
    status_seconds: float = 90.0


@dataclass
class Config:
    # Departure board.
    station: Station = field(default_factory=Station)
    display: Display = field(default_factory=Display)
    # Status board.
    status: Status = field(default_factory=Status)
    status_display: StatusDisplay = field(default_factory=StatusDisplay)
    # Both.
    refresh: Refresh = field(default_factory=Refresh)


# How each field type reads in an error message.
_EXPECTED = {
    bool: "true or false",
    int: "a whole number",
    float: "a number",
    str: "a string",
    list[str]: "a list of strings",
    list[dict]: "a list of tables",
}


def _coerce(where: str, kind, value):
    """
    Check one TOML value against its field's type. Ints stand in for floats,
    and a comma-separated string for a list of strings.
    """
    number = isinstance(value, int | float) and not isinstance(value, bool)
    if kind is bool and isinstance(value, bool):
        return value
    if kind is int and number and isinstance(value, int):
        return value
    if kind is float and number:
        return float(value)
    if kind is str and isinstance(value, str):
        return value
    if kind == list[str]:
        if isinstance(value, str):
            value = value.split(",")
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            return [v for v in value if v.strip()]
    if (
        kind == list[dict]
        and isinstance(value, list)
        and all(isinstance(v, dict) for v in value)
    ):
        return value
    raise ValueError(f"{where} should be {_EXPECTED[kind]}, not {value!r}")


def _section(cls, name: str, values):
    """
    Build one section from its TOML table, refusing keys it doesn't have so
    a typo is reported rather than quietly ignored.
    """
    if not isinstance(values, dict):
        raise ValueError(f"[{name}] should be a table")
    known = {f.name: f for f in fields(cls)}
    for key in values:
        if key not in known:
            raise ValueError(
                f"[{name}] has no setting {key!r}; it takes " + ", ".join(known)
            )
    section = cls()
    for key, value in values.items():
        setattr(
            section, key, _coerce(f"[{name}] {key}", known[key].type, value)
        )
    return section


def _check(config: Config) -> None:
    """
    Values that have the right type but can't work.
    """
    for where, value in (
        ("[station] max_rows", config.station.max_rows),
        ("[display] width", config.display.width),
        ("[display] height", config.display.height),
        ("[display] scale", config.display.scale),
        ("[display] fps", config.display.fps),
        ("[status_display] width", config.status_display.width),
        ("[status_display] height", config.status_display.height),
        ("[refresh] arrivals_seconds", config.refresh.arrivals_seconds),
        ("[refresh] status_seconds", config.refresh.status_seconds),
    ):
        if value <= 0:
            raise ValueError(f"{where} should be above 0, not {value}")
    if config.display.status_every < 0:
        raise ValueError(
            "[display] status_every should be 0 (never) or more, not "
            f"{config.display.status_every}"
        )
    show = config.station.show_line_names.strip().lower()
    if show not in SHOW_LINE_NAMES:
        raise ValueError(
            f"[station] show_line_names should be one of "
            f"{', '.join(SHOW_LINE_NAMES)}, not {show!r}"
        )
    config.station.show_line_names = show
    validate(config.status.schedule)


def load_config(path: Path | None = None) -> Config:
    """
    The defaults, overlaid with `path` or the first config file found. Raises
    `FileNotFoundError` if `path` is given but missing, and `ValueError` for
    an unknown setting or a value that can't be used.
    """
    if path is None:
        path = find_config()
    elif not path.exists():
        raise FileNotFoundError(f"No config file at {path}")
    raw: dict = {}
    if path is not None:
        with open(path, "rb") as f:
            raw = tomllib.load(f)

    station = raw.get("station")
    if isinstance(station, dict):
        # Accept the older single-value keys as well as the lists.
        for old, new in (
            ("line", "lines"),
            ("platform_contains", "platforms"),
        ):
            if value := station.pop(old, ""):
                station[new] = [value]

    sections = {f.name: f.type for f in fields(Config)}
    config = Config()
    for name, values in raw.items():
        if name not in sections:
            raise ValueError(
                f"Unknown section [{name}]; expected "
                + ", ".join(f"[{known}]" for known in sections)
            )
        setattr(config, name, _section(sections[name], name, values))
    _check(config)
    return config


def load_app_key() -> str | None:
    if key := os.environ.get("TFL_APP_KEY"):
        return key
    env_file = find_config(ENV_NAME)
    if env_file is None:
        return None
    for line in env_file.read_text().splitlines():
        name, _, value = line.partition("=")
        if name.strip() == "TFL_APP_KEY" and value.strip():
            return value.strip()
    return None


def id_list(text: str) -> list[str]:
    """
    Parse a comma-separated CLI value into lowercased IDs.
    """
    return [part.strip().lower() for part in text.split(",") if part.strip()]
