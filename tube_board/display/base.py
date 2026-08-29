"""
Output backend interface.
"""

from abc import ABC, abstractmethod


class Output(ABC):
    @abstractmethod
    def show(self, frame) -> None:
        """
        Present one native-resolution frame.
        """

    @abstractmethod
    def events(self) -> list[str]:
        """
        Return pending input events: 'quit', 'next'.
        """

    @abstractmethod
    def close(self) -> None:
        pass
