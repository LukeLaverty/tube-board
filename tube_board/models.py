"""
Data models and TfL line constants.
"""

from dataclasses import dataclass, field


@dataclass
class Departure:
    line_id: str
    line_name: str
    platform: str
    towards: str
    destination: str
    seconds: int
    current_location: str

    @property
    def countdown(self) -> str:
        # Floor rather than round.
        minutes = max(0, self.seconds) // 60
        return f"{minutes} min" if minutes else ""


@dataclass
class LineStatus:
    line_id: str
    name: str
    mode: str
    severity: int
    description: str
    reason: str | None = None

    @property
    def good(self) -> bool:
        # 10 = Good Service, 18 = No Issues.
        return self.severity in (10, 18)


@dataclass
class Snapshot:
    """
    One consistent view of the poller's data.
    """

    departures: list[Departure] = field(default_factory=list)
    statuses: list[LineStatus] = field(default_factory=list)
    arrivals_age: float = float("inf")
    status_age: float = float("inf")
    error: str | None = None


# Official TfL line colours.
LINE_COLOURS: dict[str, tuple[int, int, int]] = {
    "bakerloo": (0xB3, 0x63, 0x05),
    "central": (0xE3, 0x20, 0x17),
    "circle": (0xFF, 0xD3, 0x00),
    "district": (0x00, 0x78, 0x2A),
    "hammersmith-city": (0xF3, 0xA9, 0xBB),
    "jubilee": (0xA0, 0xA5, 0xA9),
    "metropolitan": (0x9B, 0x00, 0x56),
    "northern": (0x00, 0x00, 0x00),
    "piccadilly": (0x00, 0x36, 0x88),
    "victoria": (0x00, 0x98, 0xD4),
    "waterloo-city": (0x95, 0xCD, 0xBA),
    "elizabeth": (0x69, 0x50, 0xA1),
    "dlr": (0x00, 0xA4, 0xA7),
    "tram": (0x84, 0xB8, 0x17),
    "liberty": (0x5D, 0x60, 0x61),
    "lioness": (0xFA, 0xA6, 0x1A),
    "mildmay": (0x00, 0x77, 0xAD),
    "suffragette": (0x5B, 0xBD, 0x72),
    "weaver": (0x82, 0x3A, 0x62),
    "windrush": (0xED, 0x1B, 0x00),
    "thameslink": (0xE5, 0x00, 0x6D),
}

# Order used on station status displays: Tube A-Z, then Elizabeth line,
# Overground lines A-Z, DLR, Tram.
LINE_ORDER = [
    "bakerloo",
    "central",
    "circle",
    "district",
    "hammersmith-city",
    "jubilee",
    "metropolitan",
    "northern",
    "piccadilly",
    "victoria",
    "waterloo-city",
    "elizabeth",
    "liberty",
    "lioness",
    "mildmay",
    "suffragette",
    "weaver",
    "windrush",
    "dlr",
    "tram",
    "thameslink",
]


# Listed in LINE_ORDER for running order, but fetched as National Rail rather
# than as a TfL mode.
NON_TFL_LINE_IDS = frozenset({"thameslink"})
TFL_LINE_IDS = frozenset(LINE_ORDER) - NON_TFL_LINE_IDS


def line_sort_key(line_id: str) -> int:
    try:
        return LINE_ORDER.index(line_id)
    except ValueError:
        return len(LINE_ORDER)
