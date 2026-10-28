"""
What a board needs from the layouts it puts on the LED panel.
"""

from typing import Protocol

from ...models import Snapshot
from .theme import Canvas


class Layout(Protocol):
    def render(self, frame: Canvas, snapshot: Snapshot, dt: float) -> None:
        """
        Draw the latest data onto `frame`. `dt` is the seconds since the
        previous frame, for layouts that scroll or page.
        """


class PassLayout(Layout, Protocol):
    """
    A layout shown for one pass and then handed back, such as the status
    pages interrupting the departure list.
    """

    def restart(self, repeat: bool = False) -> None:
        """
        Start a new pass from the beginning; `repeat` loops it instead of
        finishing.
        """

    @property
    def finished(self) -> bool:
        """
        True once a non-repeating pass has shown everything.
        """
