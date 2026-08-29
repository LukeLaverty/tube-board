"""
The line status board, drawn on the LED dot-matrix panel.
"""

from collections.abc import Callable

import pygame

from ..matrix import (
    AMBER,
    DIM,
    RED,
    ROW_HEIGHT,
    WHITE,
    Fonts,
    draw_text,
)
from ..models import LINE_COLOURS, Snapshot
from .board import rows_for

TOP_Y = 2
ROW_PITCH = 12
CHIP_X = 1
CHIP_WIDTH = 5
NAME_X = 10
NAME_GAP = 5  # keeps a long line name off the status text.
DOT_SPACING = 3
DOT_ROW_HEIGHT = 2
PAGE_SECONDS = 5.0
UNKNOWN_COLOUR = (90, 90, 90)
# An unlit panel is already black, so Northern line's official black chip would
# not be there. Draw its outline instead of filling it.
MIN_CHIP_LEVEL = 90
SEVERE_MAX = 6  # TfL severities 0-6 are the serious ones.
PANEL_OFF = (0, 0, 0)
# The tube map draws these modes as a double line rather than a solid one, so
# their chips get the same hollow middle.
DOUBLE_LINE_MODES = {
    "overground",
    "dlr",
    "tram",
    "elizabeth-line",
    "national-rail",
}

# The API abbreviates this one, but the panel has room for it in full.
LONG_LINE_NAMES = {"dlr": "Docklands Light Railway"}


def status_colour(status) -> tuple[int, int, int]:
    if status.good:
        return WHITE
    return RED if status.severity <= SEVERE_MAX else AMBER


def line_name(status) -> str:
    return LONG_LINE_NAMES.get(status.line_id, status.name)


class StatusScreen:
    """
    Every line's service status, paged.
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
        Start a fresh pass at the first page.

        `repeat` keeps cycling once every page has been shown; otherwise the
        pass holds on its last page and `finished` goes True, so a caller can
        hand the panel back to whatever it interrupted.
        """
        self._repeat = repeat
        self._page = 0
        self._elapsed = 0.0
        self._finished = False
        # Re-read per pass, so a schedule that rolls over midnight is picked up.
        self._selected = self._selection() if self._selection else None

    @property
    def finished(self) -> bool:
        """
        True once every page has had its turn.
        """
        return self._finished

    def render(
        self, frame: pygame.Surface, snapshot: Snapshot, dt: float
    ) -> None:
        width, height = frame.get_width(), frame.get_height()
        font = self._fonts.text

        rows = rows_for(snapshot.statuses, self._selected)
        if not rows:
            draw_text(
                frame,
                font,
                "Service information unavailable",
                width // 2,
                max(0, (height - ROW_HEIGHT) // 2),
                AMBER,
                align="center",
            )
            # Still time out, or the panel would sit here with nothing to show.
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
                # Holds here rather than flashing page 1 again for the frame
                # before the caller takes the panel back.
                self._page = 0 if self._repeat else pages - 1
        # Re-clamp: the line count changes as statuses come and go.
        self._page = min(self._page, pages - 1)

        start = self._page * per_page
        for i, status in enumerate(rows[start : start + per_page]):
            self._render_row(frame, status, TOP_Y + i * ROW_PITCH, width)

        if pages > 1:
            self._render_page_dots(frame, pages, width, height)

    def _render_row(self, frame, status, y: int, width: int) -> None:
        font = self._fonts.text
        colour = LINE_COLOURS.get(status.line_id, UNKNOWN_COLOUR)
        chip = pygame.Rect(CHIP_X, y, CHIP_WIDTH, ROW_HEIGHT)
        if max(colour) < MIN_CHIP_LEVEL:
            # Black cannot light an LED, so outline the chip instead.
            pygame.draw.rect(frame, WHITE, chip, width=1)
        else:
            frame.fill(colour, chip)
            if status.mode in DOUBLE_LINE_MODES:
                frame.fill(
                    PANEL_OFF,
                    pygame.Rect(CHIP_X + CHIP_WIDTH // 2, y, 1, ROW_HEIGHT),
                )

        status_x = width - 2
        status_width = font.size(status.description)[0]
        draw_text(
            frame,
            font,
            status.description,
            status_x,
            y,
            status_colour(status),
            align="right",
        )

        # Name gives way to the status, never the other way round.
        available = status_x - status_width - NAME_GAP - NAME_X
        if available > 0:
            frame.set_clip(pygame.Rect(NAME_X, y, available, ROW_HEIGHT))
            draw_text(frame, font, line_name(status), NAME_X, y, WHITE)
            frame.set_clip(None)

    def _render_page_dots(
        self, frame, pages: int, width: int, height: int
    ) -> None:
        span = (pages - 1) * DOT_SPACING
        x = (width - span) // 2
        y = height - DOT_ROW_HEIGHT
        for page in range(pages):
            frame.set_at(
                (x + page * DOT_SPACING, y),
                WHITE if page == self._page else DIM,
            )
