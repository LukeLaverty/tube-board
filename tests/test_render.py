"""
Golden-image tests for the LED layouts.

Each case is compared to a stored PNG. After an intended change, regenerate
them with `UPDATE_GOLDENS=1` and check the diff.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image, ImageChops

from tube_board.config import load_config
from tube_board.models import Departure, Snapshot
from tube_board.render.led.departures import DeparturesLayout
from tube_board.render.led.status import StatusLayout
from tube_board.render.led.theme import Canvas, Fonts
from tube_board.sources.mock import MOCK_STATUSES, mock_snapshot

GOLDEN = Path(__file__).parent / "golden"
SIZE = (256, 64)
FRAME_DT = 1 / 30
# Frozen so the bottom-row clock matches between runs.
CLOCK = "09:41:07"

MIXED_LINES = Snapshot(
    departures=[
        Departure(
            "circle",
            "Circle",
            "Platform 1",
            "Edgware Road",
            "Edgware Road",
            45,
            "",
        ),
        Departure(
            "district",
            "District",
            "Platform 1",
            "Upminster",
            "Upminster",
            200,
            "",
        ),
        Departure(
            "hammersmith-city",
            "Hammersmith & City",
            "Platform 1",
            "Barking",
            "Barking",
            480,
            "",
        ),
    ],
    statuses=list(MOCK_STATUSES),
    arrivals_age=1.0,
    status_age=1.0,
)


@pytest.fixture(scope="module")
def fonts():
    return Fonts()


def _render(layout, snapshot, dt=FRAME_DT) -> Image.Image:
    canvas = Canvas(SIZE)
    layout.render(canvas, snapshot, dt)
    return canvas.image


def departures_clock(fonts):
    """The default panel: no ticker, as the status layout interrupts."""
    return _render(
        DeparturesLayout(fonts, load_config(), ticker=False), mock_snapshot()
    )


def departures_ticker(fonts):
    """The ticker scrolling a disruption reason under the clock."""
    layout = DeparturesLayout(fonts, load_config(), ticker=True)
    for _ in range(30):  # scroll for a second.
        _render(layout, mock_snapshot())
    return _render(layout, mock_snapshot())


def departures_stale(fonts):
    """No arrivals data for long enough to fall back to the announcement."""
    snapshot = mock_snapshot()
    snapshot.arrivals_age = 999.0
    return _render(
        DeparturesLayout(fonts, load_config(), ticker=False), snapshot
    )


def departures_mixed_lines(fonts):
    """More than one line on the board, so the line-name column appears."""
    config = load_config()
    config["station"]["platforms"] = []
    return _render(DeparturesLayout(fonts, config, ticker=False), MIXED_LINES)


def status_page1(fonts):
    return _render(StatusLayout(fonts), mock_snapshot(), dt=0.0)


def status_page2(fonts):
    """The second page, and so also the page dots."""
    layout = StatusLayout(fonts)
    _render(layout, mock_snapshot(), dt=0.0)
    _render(layout, mock_snapshot(), dt=5.0)  # next page.
    return _render(layout, mock_snapshot(), dt=0.0)


def status_empty(fonts):
    return _render(
        StatusLayout(fonts),
        Snapshot(arrivals_age=1.0, status_age=1.0),
        dt=0.0,
    )


CASES = [
    departures_clock,
    departures_ticker,
    departures_stale,
    departures_mixed_lines,
    status_page1,
    status_page2,
    status_empty,
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.__name__)
def test_matches_golden(case, fonts):
    with patch("time.strftime", lambda fmt: CLOCK):
        rendered = case(fonts)

    path = GOLDEN / f"{case.__name__}.png"
    if os.environ.get("UPDATE_GOLDENS"):
        rendered.save(path)
        pytest.skip(f"rewrote {path.name}")

    assert path.exists(), f"no golden for {case.__name__}; UPDATE_GOLDENS=1"
    expected = Image.open(path).convert("RGB")
    assert rendered.size == expected.size
    box = ImageChops.difference(rendered, expected).getbbox()
    if box is None:
        return
    differing = sum(
        1
        for y in range(box[1], box[3])
        for x in range(box[0], box[2])
        if rendered.getpixel((x, y)) != expected.getpixel((x, y))
    )
    raise AssertionError(
        f"{differing} pixels differ from {path.name}, within {box}"
    )
