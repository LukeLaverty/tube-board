"""
A board turns data into an image. Windows, files and input are left to
drivers, so any board works with any driver.
"""

from abc import ABC, abstractmethod

from PIL import Image


class Board(ABC):
    def __init__(self, size: tuple[int, int]):
        # The frame size in pixels, which a driver sizes its target to.
        self.size = size

    @abstractmethod
    def frame(self, dt: float) -> Image.Image:
        """
        Render the next frame. `dt` is the seconds since the last one.
        """

    def handle(self, event: str) -> None:
        """
        Handle an input event. The runner handles 'quit' itself.
        """
        return

    @property
    def finished(self) -> bool:
        """
        True when the runner should stop. Boards that run indefinitely leave
        this False.
        """
        return False
