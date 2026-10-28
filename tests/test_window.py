"""
The Pygame preview window, run headless.
"""

import pytest
from PIL import Image

pygame = pytest.importorskip("pygame")

from tube_board.drivers.window import Window  # noqa: E402


@pytest.fixture
def flips(monkeypatch):
    count = []
    monkeypatch.setattr(pygame.display, "flip", lambda: count.append(1))
    return count


@pytest.mark.parametrize("dot_matrix", [False, True])
def test_an_unchanged_frame_is_not_redrawn(flips, dot_matrix):
    with Window(8, 4, 2, dot_matrix=dot_matrix, headless=True) as window:
        frame = Image.new("RGB", (8, 4))
        window.show(frame)
        window.show(frame)
        assert len(flips) == 1
        window.show(Image.new("RGB", (8, 4)))
        assert len(flips) == 2


def test_the_plain_window_builds_no_lamp_grid():
    with Window(8, 4, headless=True) as window:
        assert window._background is None
