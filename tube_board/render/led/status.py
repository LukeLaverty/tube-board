"""
The line status board, drawn on the LED dot-matrix panel.
"""

from collections.abc import Callable

from ...models import LINE_COLOURS, UNKNOWN_COLOUR, Colour, Snapshot
from ...selection import rows_for
from .theme import (
    AMBER,
    DIM,
    OFF,
    RED,
    ROW_HEIGHT,
    WHITE,
    Canvas,
    Fonts,
)

TOP_Y = 2
ROW_PITCH = 12
CHIP_X = 1
CHIP_WIDTH = 5
NAME_X = 10
NAME_GAP = 5  # keeps a long line name off the status text.
DOT_SPACING = 3
DOT_ROW_HEIGHT = 2
PAGE_SECONDS = 5.0
# Chips darker than this, such as the Northern line's black, would not show
# on the panel, so they are outlined instead.
MIN_CHIP_LEVEL = 90
# Hollow chips, as the tube map draws these as double lines.
DOUBLE_LINE_MODES = {
    "overground",
    "dlr",
    "tram",
    "elizabeth-line",
    "national-rail",
}

# The API abbreviates this one, but the panel has room for it in full.
LONG_LINE_NAMES = {"dlr": "Docklands Light Railway"}


def status_colour(status) -> Colour:
    if status.good:
        return WHITE
    return RED if status.severe else AMBER


def line_name(status) -> str:
    return LONG_LINE_NAMES.get(status.line_id, status.name)


class StatusLayout:
    """
    Line statuses, a page at a time.
    """

    def __init__(
        self,
        fonts: Fonts,
        selection: Callable[[], list[str]] | None = None,
    ):
        self._fonts = fonts
        self._selection = selection
        self._selected: list[str] | None = None
        self._page = 0
        self._elapsed = 0.0
        self._finished = False
        self._repeat = False
        self.restart()

    def restart(self, repeat: bool = False) -> None:
        """
        Start a pass at the first page. With `repeat` it keeps cycling;
        otherwise it holds the last page and sets `finished`.
        """
        self._repeat = repeat
        self._page = 0
        self._elapsed = 0.0
        self._finished = False
        # Re-read each pass so the schedule rolls over at midnight.
        self._selected = self._selection() if self._selection else None

    @property
    def finished(self) -> bool:
        """
        True once every page has had its turn.
        """
        return self._finished

    def render(self, frame: Canvas, snapshot: Snapshot, dt: float) -> None:
        width, height = frame.width, frame.height
        font = self._fonts.text

        rows = rows_for(snapshot.statuses, self._selected)
        if not rows:
            frame.text(
                font,
                "Service information unavailable",
                width // 2,
                max(0, (height - ROW_HEIGHT) // 2),
                AMBER,
                align="center",
            )
            # Still finish, so the panel is handed back.
            self._elapsed += dt
            if self._elapsed >= PAGE_SECONDS:
                self._finished = True
            return

        per_page = max(1, (height - TOP_Y - DOT_ROW_HEIGHT) // ROW_PITCH)
        pages = (len(rows) + per_page - 1) // per_page

        self._elapsed += dt
        if self._elapsed >= PAGE_SECONDS:
            self._elapsed = 0.0
            if self._page + 1 < pages:
                self._page += 1
            else:
                self._finished = True
                # Hold the last page so page 1 doesn't flash before the
                # handback.
                self._page = 0 if self._repeat else pages - 1
        # The line count can change between frames.
        self._page = min(self._page, pages - 1)

        start = self._page * per_page
        for i, status in enumerate(rows[start : start + per_page]):
            self._render_row(frame, status, TOP_Y + i * ROW_PITCH, width)

        if pages > 1:
            self._render_page_dots(frame, pages, width, height)

    def _render_row(self, frame: Canvas, status, y: int, width: int) -> None:
        font = self._fonts.text
        colour = LINE_COLOURS.get(status.line_id, UNKNOWN_COLOUR)
        if max(colour) < MIN_CHIP_LEVEL:
            frame.outline(CHIP_X, y, CHIP_WIDTH, ROW_HEIGHT, WHITE)
        else:
            frame.rect(CHIP_X, y, CHIP_WIDTH, ROW_HEIGHT, colour)
            if status.mode in DOUBLE_LINE_MODES:
                frame.rect(CHIP_X + CHIP_WIDTH // 2, y, 1, ROW_HEIGHT, OFF)

        status_x = width - 2
        status_width = font.width(status.description)
        frame.text(
            font,
            status.description,
            status_x,
            y,
            status_colour(status),
            align="right",
        )

        # The name is clipped to leave room for the status.
        available = status_x - status_width - NAME_GAP - NAME_X
        if available > 0:
            frame.text(
                font,
                line_name(status),
                NAME_X,
                y,
                WHITE,
                clip=(NAME_X, y, available, ROW_HEIGHT),
            )

    def _render_page_dots(
        self, frame: Canvas, pages: int, width: int, height: int
    ) -> None:
        span = (pages - 1) * DOT_SPACING
        x = (width - span) // 2
        y = height - DOT_ROW_HEIGHT
        for page in range(pages):
            frame.pixel(
                x + page * DOT_SPACING,
                y,
                WHITE if page == self._page else DIM,
            )
