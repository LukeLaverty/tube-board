"""
The shared frame loop: routing events, stopping, and timing.
"""

from PIL import Image

from tube_board import runner
from tube_board.boards import Board
from tube_board.drivers import Driver

FRAME = Image.new("RGB", (4, 4))


class FakeBoard(Board):
    def __init__(self, finish_after: int | None = None):
        super().__init__((4, 4))
        self.events: list[str] = []
        self.dts: list[float] = []
        self._finish_after = finish_after

    def frame(self, dt: float) -> Image.Image:
        self.dts.append(dt)
        return FRAME

    def handle(self, event: str) -> None:
        self.events.append(event)

    @property
    def finished(self) -> bool:
        return (
            self._finish_after is not None
            and len(self.dts) >= self._finish_after
        )


class FakeDriver(Driver):
    def __init__(self, events: list[list[str]] | None = None):
        self.shown = 0
        self._events = list(events or [])

    def show(self, frame: Image.Image) -> None:
        self.shown += 1

    def events(self) -> list[str]:
        return self._events.pop(0) if self._events else []


def test_stops_after_the_requested_frames():
    driver = FakeDriver()
    assert runner.run(FakeBoard(), driver, fps=0, frames=3) == 3
    assert driver.shown == 3


def test_stops_when_the_board_finishes():
    assert runner.run(FakeBoard(finish_after=2), FakeDriver(), fps=0) == 2


def test_quit_stops_before_another_frame_is_shown():
    driver = FakeDriver([[], ["quit"]])
    assert runner.run(FakeBoard(), driver, fps=0) == 1


def test_other_events_go_to_the_board():
    board = FakeBoard()
    runner.run(board, FakeDriver([["next", "refresh"]]), fps=0, frames=1)
    assert board.events == ["next", "refresh"]


def test_a_fixed_timestep_replaces_the_wall_clock():
    board = FakeBoard()
    runner.run(board, FakeDriver(), fps=0, frames=3, fixed_dt=0.5)
    assert board.dts == [0.5, 0.5, 0.5]
