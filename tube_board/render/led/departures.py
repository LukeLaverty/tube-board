"""
The departure list, as on a platform's "next train indicator".
"""

import time

from ...models import Snapshot
from .theme import AMBER, GLYPH_HEIGHT, OFF, ROW_HEIGHT, Canvas, Fonts

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
    1st, 2nd, 3rd, 4th...
    """
    # 11th, 12th and 13th, not 11st.
    suffix = "th" if 11 <= n % 100 <= 13 else ORDINAL_SUFFIXES.get(n % 10, "th")
    return f"{n}{suffix}"


class DeparturesLayout:
    def __init__(self, fonts: Fonts, config: dict, ticker: bool = True):
        self._fonts = fonts
        # Off when the status layout interrupts on a timer, which leaves the
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
        self._ticker_offset = 0.0
        # Rendered when the text changes and pasted each frame.
        self._ticker_text = ""
        self._ticker_strip: Canvas | None = None

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

    def render(self, frame: Canvas, snapshot: Snapshot, dt: float) -> None:
        width = frame.width
        font = self._fonts.text
        bottom_y = frame.height - BOTTOM_ROW_HEIGHT

        if snapshot.arrivals_age > STALE_AFTER:
            frame.text(
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
        # Sized to the widest rank shown, so "10th" only widens it when it is
        # there.
        ranks = [ordinal(i + 1) for i in range(len(rows))]
        rank_column = max((font.width(r) for r in ranks), default=0) + 5
        for i, dep in enumerate(rows):
            y = 1 + i * pitch
            frame.text(font, ranks[i], 1, y, AMBER)
            cd_width = frame.text(
                font, dep.countdown, countdown_x, y, AMBER, align="right"
            )
            if line_column:
                frame.text(
                    font,
                    short_line_name(dep),
                    rank_column,
                    y,
                    AMBER,
                    clip=(rank_column, y, line_column - 4, ROW_HEIGHT),
                )
            destination_x = rank_column + line_column
            available = countdown_x - cd_width - 5 - destination_x
            frame.text(
                font,
                dep.towards,
                destination_x,
                y,
                AMBER,
                clip=(destination_x, y, available, ROW_HEIGHT),
            )

        self._render_bottom_row(frame, snapshot, dt)

    def _layout(self, snapshot: Snapshot, bottom_y: int):
        """
        The font has one usable size, so more rows means a tighter pitch.
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
        return max(font.width(short_line_name(d)) for d in rows) + 5

    def _render_bottom_row(self, frame: Canvas, snapshot, dt) -> None:
        width = frame.width
        font = self._fonts.text
        y = frame.height - BOTTOM_ROW_HEIGHT + 1
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
            frame.text(font, clock_text, width // 2, y, AMBER, align="center")
            return

        if text != self._ticker_text or self._ticker_strip is None:
            self._ticker_text = text
            self._ticker_strip = Canvas(
                (max(1, font.width(text)), frame.height - y)
            )
            self._ticker_strip.text(font, text, 0, 0, AMBER)
        strip = self._ticker_strip

        self._ticker_offset += dt * TICKER_SPEED
        x = width - self._ticker_offset
        if x < -strip.width:
            self._ticker_offset = 0.0
            x = width
        frame.paste(strip.image, round(x), y)

        # Clock sits on top at the right; the ticker slides underneath it.
        clock_width = font.width(clock_text)
        frame.rect(
            width - clock_width - 6,
            y - 1,
            clock_width + 8,
            ROW_HEIGHT + 2,
            OFF,
        )
        frame.text(font, clock_text, width - 2, y, AMBER, align="right")
