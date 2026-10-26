"""
Keeps the last frame for saving to a file, for cron jobs and e-ink.
"""

from PIL import Image

from .base import Driver


class PngFile(Driver):
    def __init__(self):
        self._last: Image.Image | None = None

    def show(self, frame: Image.Image) -> None:
        self._last = frame

    def save(self, path: str) -> None:
        if self._last is None:
            raise RuntimeError("nothing has been rendered yet")
        self._last.save(path)
