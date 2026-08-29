"""
Departure board layout drawn onto a native-resolution Pygame Surface.
"""

import time

import pygame

from ..matrix import (
    AMBER,
    GLYPH_HEIGHT,
    ROW_HEIGHT,
    Fonts,
    draw_text,
)
from ..models import Snapshot

TICKER_SPEED = 40  # native pixels per second.
STALE_AFTER = 150  # seconds without data before the fallback message.
PREFERRED_PITCH = 13
MIN_PITCH = 11
BOTTOM_ROW_HEIGHT = 12


SHORT_LINE_NAMES = {
    "hammersmith-city": "H'smith & City",
    "waterloo-city": "W'loo & City",
    "elizabeth": "Elizabeth",  # usually 'Elizabeth line'.
}


def short_line_name(departure) -> str:
    return SHORT_LINE_NAMES.get(departure.line_id, departure.line_name)


ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}


def ordinal(n: int) -> str:
    """
    1st, 2nd, 3rd, 4th - how a platform indicator ranks its trains.
    """
    # Teens break the last-digit rule: 11th, 12th, 13th, not 11st.
    suffix = "th" if 11 <= n % 100 <= 13 else ORDINAL_SUFFIXES.get(n % 10, "th")
    return f"{n}{suffix}"


class DeparturesScreen:
    """
    The classic platform 'next train indicator'.
    """

    def __init__(self, fonts: Fonts, config: dict, ticker: bool = True):
        self._fonts = fonts
        # The scrolling reason ticker is redundant when the status board takes
        # the panel on a timer, so the caller can turn it off and leave the
        # bottom row to the clock.
        self._ticker = ticker
        station = config["station"]
        self._lines = [
            line.strip().lower() for line in station["lines"] if line.strip()
        ]
        self._platforms = [
            platform.strip().lower()
            for platform in station["platforms"]
            if platform.strip()
        ]
        self._max_rows = int(station["max_rows"])
        self._show_line_names = str(station["show_line_names"]).strip().lower()
        self._ticker_text = ""
        self._ticker_surf: pygame.Surface | None = None
        self._ticker_offset = 0.0

    def _filtered(self, snapshot: Snapshot, limit: int):
        rows = snapshot.departures
        if self._lines:
            rows = [
                departure
                for departure in rows
                if departure.line_id in self._lines
            ]
        if self._platforms:
            rows = [
                departure
                for departure in rows
                if any(
                    platform in departure.platform.lower()
                    for platform in self._platforms
                )
            ]
        return rows[:limit]

    def render(
        self, frame: pygame.Surface, snapshot: Snapshot, dt: float
    ) -> None:
        width = frame.get_width()
        font = self._fonts.text
        bottom_y = frame.get_height() - BOTTOM_ROW_HEIGHT

        if snapshot.arrivals_age > STALE_AFTER:
            draw_text(
                frame,
                font,
                "Please listen for announcements",
                width // 2,
                max(0, (bottom_y - GLYPH_HEIGHT) // 2),
                AMBER,
                align="center",
            )
            self._render_bottom_row(frame, snapshot, dt)
            return

        pitch, rows, line_column = self._layout(snapshot, bottom_y)
        countdown_x = width - 2
        # Size the rank column for the widest ordinal actually on the board,
        # so "10th" does not shunt the destinations along on a taller panel.
        ranks = [ordinal(i + 1) for i in range(len(rows))]
        rank_column = max((font.size(r)[0] for r in ranks), default=0) + 5
        for i, dep in enumerate(rows):
            y = 1 + i * pitch
            draw_text(frame, font, ranks[i], 1, y, AMBER)
            cd_width = draw_text(
                frame,
                font,
                dep.countdown,
                countdown_x,
                y,
                AMBER,
                align="right",
            )
            if line_column:
                frame.set_clip(
                    pygame.Rect(rank_column, y, line_column - 4, ROW_HEIGHT)
                )
                draw_text(
                    frame,
                    font,
                    short_line_name(dep),
                    rank_column,
                    y,
                    AMBER,
                )
                frame.set_clip(None)
            destination_x = rank_column + line_column
            available = countdown_x - cd_width - 5 - destination_x
            frame.set_clip(pygame.Rect(destination_x, y, available, ROW_HEIGHT))
            draw_text(frame, font, dep.towards, destination_x, y, AMBER)
            frame.set_clip(None)

        self._render_bottom_row(frame, snapshot, dt)

    def _layout(self, snapshot: Snapshot, bottom_y: int):
        """
        Only the row spacing flexes: the font has exactly one usable size,
        so more rows means tighter pitch rather than smaller text.
        """
        pitch = PREFERRED_PITCH
        if self._max_rows * pitch > bottom_y:
            pitch = max(MIN_PITCH, bottom_y // max(1, self._max_rows))
        rows = self._filtered(
            snapshot, max(1, min(self._max_rows, bottom_y // pitch))
        )
        return pitch, rows, self._line_column_width(rows)

    def _line_column_width(self, rows) -> int:
        if self._show_line_names == "never" or not rows:
            return 0
        if (
            self._show_line_names == "auto"
            and len({d.line_id for d in rows}) < 2
        ):
            return 0
        font = self._fonts.text
        return max(font.size(short_line_name(d))[0] for d in rows) + 5

    def _render_bottom_row(self, frame, snapshot, dt) -> None:
        width = frame.get_width()
        font = self._fonts.text
        y = frame.get_height() - BOTTOM_ROW_HEIGHT + 1
        clock_text = time.strftime("%H:%M:%S")

        text = ""
        if self._ticker:
            reasons = [
                status.reason
                for status in snapshot.statuses
                if not status.good and status.reason
            ]
            text = "  *  ".join(dict.fromkeys(reasons))
        if not text:
            self._ticker_surf = None
            self._ticker_text = ""
            draw_text(
                frame,
                font,
                clock_text,
                width // 2,
                y,
                AMBER,
                align="center",
            )
            return

        if text != self._ticker_text:
            self._ticker_text = text
            self._ticker_surf = font.render(text, False, AMBER)
        self._ticker_offset += dt * TICKER_SPEED
        x = width - self._ticker_offset
        if x < -self._ticker_surf.get_width():
            self._ticker_offset = 0.0
            x = width
        frame.blit(self._ticker_surf, (round(x), y))

        # Clock sits on top at the right; the ticker slides underneath it.
        clock_width = font.size(clock_text)[0]
        frame.fill(
            (0, 0, 0),
            pygame.Rect(
                width - clock_width - 6,
                y - 1,
                clock_width + 8,
                ROW_HEIGHT + 2,
            ),
        )
        draw_text(
            frame,
            font,
            clock_text,
            width - 2,
            y,
            AMBER,
            align="right",
        )
