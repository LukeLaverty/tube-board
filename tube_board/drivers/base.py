"""
A driver shows frames on one target, such as a window, a file or a panel,
without knowing what they contain. Frames are Pillow images at the board's
native size.
"""

from abc import ABC, abstractmethod

from PIL import Image


class Driver(ABC):
    @abstractmethod
    def show(self, frame: Image.Image) -> None:
        """
        Present one finished frame.
        """

    def events(self) -> list[str]:
        """
        Pending input events: 'quit', 'next', 'refresh'.
        """
        return []

    def save(self, path: str) -> None:
        """
        Save the last frame shown.
        """
        raise NotImplementedError(f"{type(self).__name__} cannot save a file")

    def close(self) -> None:
        """
        Release the target.
        """
        return

    def __enter__(self):
        return self

    def __exit__(self, *exception) -> None:
        self.close()
