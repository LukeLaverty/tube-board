"""
Paths, defaults and config loading.
"""

import os
import tomllib
from pathlib import Path

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


DEFAULTS = {
    # Departure board.
    "station": {
        "name": "King's Cross St. Pancras",
        "id": "940GZZLUKSX",
        "lines": [],
        "platforms": [],
        "show_line_names": "auto",
        "max_rows": 3,
    },
    "display": {
        "width": 256,
        "height": 64,
        "scale": 6,
        "fps": 30,
        "status_every": 60,
        "status_follows_schedule": False,
    },
    # Status board.
    "status": {"lines": [], "schedule": []},
    "status_display": {"width": 800, "height": 480},
    # Both.
    "refresh": {"arrivals_seconds": 10, "status_seconds": 90},
}


def load_config(path: Path | None = None) -> dict:
    """
    The defaults, overlaid with `path` or the first config file found. Raises
    `FileNotFoundError` if `path` is given but missing.
    """
    if path is None:
        path = find_config()
    elif not path.exists():
        raise FileNotFoundError(f"No config file at {path}")
    config = {section: dict(values) for section, values in DEFAULTS.items()}
    if path is not None:
        with open(path, "rb") as f:
            for section, values in tomllib.load(f).items():
                config.setdefault(section, {}).update(values)
    station = config["station"]
    # Accept single-value keys as well as the lists.
    for old, new in (
        ("line", "lines"),
        ("platform_contains", "platforms"),
    ):
        if value := station.pop(old, ""):
            station[new] = [value]
    for key in ("lines", "platforms"):
        if isinstance(station[key], str):
            station[key] = [p for p in station[key].split(",") if p.strip()]
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
