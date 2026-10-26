"""
The LED panel board: departures, with a pass of line statuses on a timer.
"""

import math
import time
from collections.abc import Callable

from PIL import Image

from ..models import Snapshot
from ..render.led.departures import DeparturesLayout
from ..render.led.status import StatusLayout
from ..render.led.theme import Canvas, Fonts
from .base import Board


def _next_minute(now: float) -> float:
    """
    The next whole minute on the wall clock.
    """
    return math.floor(now / 60) * 60 + 60


def _advance(next_at: float, every: float, now: float) -> float:
    """
    Move a trigger to the first slot after `now`, skipping any missed while
    the status layout held the panel.
    """
    if every <= 0:
        return next_at
    while next_at <= now:
        next_at += every
    return next_at


class PanelBoard(Board):
    """
    Shows departures, and every `status_every` seconds one pass of the status
    layout. 'next' (Tab) toggles the status layout and pins it.
    """

    def __init__(
        self,
        config: dict,
        get_snapshot: Callable[[], Snapshot],
        *,
        selection: Callable[[], list[str]] | None = None,
        wall_clock: bool = True,
    ):
        display = config["display"]
        super().__init__((int(display["width"]), int(display["height"])))
        self._get_snapshot = get_snapshot
        self._status_every = float(display.get("status_every", 0) or 0)
        # On the wall clock, passes land on whole minutes. Headless renders
        # count synthetic seconds so they don't wait in real time.
        self._wall_clock = wall_clock
        self._elapsed = 0.0

        fonts = Fonts()
        self._status = StatusLayout(fonts, selection)
        self._layouts = (
            DeparturesLayout(fonts, config, ticker=not self._status_every),
            self._status,
        )
        self._current = 0
        self._pinned = False
        self._next_status = 0.0
        if self._status_every:
            self._next_status = (
                _next_minute(time.time()) if wall_clock else self._status_every
            )

    def _now(self) -> float:
        return time.time() if self._wall_clock else self._elapsed

    def handle(self, event: str) -> None:
        if event != "next":
            return
        self._current = 1 - self._current
        self._pinned = self._current == 1
        if self._pinned:
            self._status.restart(repeat=True)
        else:
            self._next_status = _advance(
                self._next_status, self._status_every, self._now()
            )

    def frame(self, dt: float) -> Image.Image:
        self._elapsed += dt
        now = self._now()

        if self._current == 0:
            if self._status_every and now >= self._next_status:
                self._current, self._pinned = 1, False
                self._status.restart()
                self._next_status = _advance(
                    self._next_status, self._status_every, now
                )
        elif not self._pinned and self._status.finished:
            self._current = 0
            self._next_status = _advance(
                self._next_status, self._status_every, now
            )

        canvas = Canvas(self.size)
        self._layouts[self._current].render(canvas, self._get_snapshot(), dt)
        return canvas.image
