"""
The frame loop shared by every board.
"""

import time

from .boards import Board
from .drivers import Driver


def run(
    board: Board,
    driver: Driver,
    *,
    fps: int = 30,
    frames: int | None = None,
    fixed_dt: float | None = None,
) -> int:
    """
    Run until the board finishes or the driver quits, and return the number of
    frames shown. The caller closes the driver, so it can still save the last
    frame afterwards.

    `frames` caps the frame count. `fixed_dt` replaces the wall clock with a
    fixed timestep, for headless renders.
    """
    interval = 1.0 / fps if fps else 0.0
    previous = time.monotonic()
    shown = 0

    while True:
        started = time.monotonic()
        dt = fixed_dt if fixed_dt is not None else started - previous
        previous = started

        stopping = False
        for event in driver.events():
            if event == "quit":
                stopping = True
            else:
                board.handle(event)
        if stopping:
            break

        driver.show(board.frame(dt))
        shown += 1

        if board.finished or (frames is not None and shown >= frames):
            break

        if fixed_dt is None and interval:
            elapsed = time.monotonic() - started
            time.sleep(max(0.0, interval - elapsed))
    return shown
