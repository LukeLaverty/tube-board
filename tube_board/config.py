"""
Paths, defaults and config loading.
"""

import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_DIRECTORY = ROOT / "fonts"
CONFIG_FILE = ROOT / "config.toml"

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


def load_config(path: Path = CONFIG_FILE) -> dict:
    config = {section: dict(values) for section, values in DEFAULTS.items()}
    if path.exists():
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
    env_file = ROOT / ".env"
    if env_file.exists():
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
