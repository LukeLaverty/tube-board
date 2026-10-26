"""
The "Service Information" board: the paper layout, refetched on a timer.
"""

import time
from collections.abc import Callable
from datetime import datetime

from PIL import Image

from ..models import LineStatus
from ..render.paper.status import render_status_image
from ..selection import selection_for
from .base import Board


class StatusPaperBoard(Board):
    def __init__(
        self,
        config: dict,
        fetch: Callable[[list[str]], list[LineStatus]],
        *,
        override: list[str] | None = None,
        weekday: int | None = None,
    ):
        display = config["status_display"]
        super().__init__((int(display["width"]), int(display["height"])))
        self._config = config
        self._fetch = fetch
        self._override = override
        self._weekday = weekday
        self._refresh_every = float(config["refresh"]["status_seconds"])
        self._statuses: list[LineStatus] = []
        self._updated: datetime | None = None
        self._last_success = 0.0
        self._next_fetch = 0.0
        self._image: Image.Image | None = None

    @property
    def fetched(self) -> bool:
        """
        Whether any fetch has succeeded, so a one-shot render can report a
        failure instead of saving an empty board.
        """
        return self._last_success > 0.0

    def handle(self, event: str) -> None:
        if event == "refresh":
            self._next_fetch = 0.0

    def frame(self, dt: float) -> Image.Image:
        now = time.monotonic()
        if self._image is None or now >= self._next_fetch:
            self._next_fetch = now + self._refresh_every
            # Re-read each time so the schedule rolls over at midnight.
            selected = selection_for(
                self._config, self._override, self._weekday
            )
            try:
                self._statuses = self._fetch(selected)
                self._updated = datetime.now()
                self._last_success = now
            except OSError:
                # Requests' exceptions are OSErrors. Keep the last good data
                # and let the board show it is offline.
                pass
            offline = (
                now - self._last_success > self._refresh_every * 2
                if self._last_success
                else True
            )
            self._image = render_status_image(
                self._statuses,
                self.size,
                selected,
                self._updated,
                offline,
            )
        return self._image
