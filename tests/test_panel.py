"""
The LED panel's state machine: when the status board interrupts the departure
list, and when it hands the panel back.
"""

from tube_board.boards.panel import PanelBoard, _advance, _next_minute
from tube_board.render.led.status import PAGE_SECONDS
from tube_board.sources.mock import mock_snapshot

# Coarse steps: these tests check timers, not animation.
FRAME = 0.25


def board(status_every: float = 5.0) -> PanelBoard:
    config = {
        "station": {
            "name": "Test",
            "lines": [],
            "platforms": [],
            "show_line_names": "auto",
            "max_rows": 3,
        },
        "display": {
            "width": 256,
            "height": 64,
            "status_every": status_every,
        },
    }
    # Synthetic seconds, so tests don't wait for a real minute.
    return PanelBoard(config, mock_snapshot, wall_clock=False)


def run_for(panel: PanelBoard, seconds: float) -> None:
    for _ in range(round(seconds / FRAME)):
        panel.frame(FRAME)


def showing(panel: PanelBoard) -> str:
    return "status" if panel._current else "departures"


class TestNextMinute:
    def test_rounds_up_to_the_next_whole_minute(self):
        assert _next_minute(100.0) == 120.0

    def test_a_whole_minute_moves_on_to_the_following_one(self):
        assert _next_minute(120.0) == 180.0


class TestAdvance:
    def test_moves_past_now(self):
        assert _advance(10.0, 5.0, 12.0) == 15.0

    def test_skips_every_slot_missed_while_the_panel_was_held(self):
        # A pass that overran three intervals must not fire three times.
        assert _advance(10.0, 5.0, 27.0) == 30.0

    def test_leaves_the_trigger_alone_when_there_is_no_interval(self):
        assert _advance(10.0, 0.0, 99.0) == 10.0


class TestStatusInterrupt:
    def test_starts_on_the_departure_list(self):
        assert showing(board()) == "departures"

    def test_status_takes_over_on_the_timer(self):
        panel = board(status_every=5.0)
        run_for(panel, 4.0)
        assert showing(panel) == "departures"
        run_for(panel, 1.5)
        assert showing(panel) == "status"

    def test_and_hands_the_panel_back_after_one_pass(self):
        panel = board(status_every=5.0)
        run_for(panel, 5.5)
        assert showing(panel) == "status"
        # Three pages of mock statuses, each held for `PAGE_SECONDS`.
        run_for(panel, PAGE_SECONDS * 3 + 1)
        assert showing(panel) == "departures"

    def test_never_interrupts_when_the_interval_is_zero(self):
        panel = board(status_every=0.0)
        run_for(panel, 60.0)
        assert showing(panel) == "departures"


class TestPinning:
    def test_tab_calls_the_status_board_up_and_pins_it(self):
        panel = board(status_every=5.0)
        panel.handle("next")
        assert showing(panel) == "status"
        # Pinned, so it keeps cycling instead of handing the panel back.
        run_for(panel, PAGE_SECONDS * 4 + 1)
        assert showing(panel) == "status"

    def test_tab_again_hands_it_back(self):
        panel = board(status_every=5.0)
        panel.handle("next")
        panel.handle("next")
        assert showing(panel) == "departures"

    def test_an_unknown_event_changes_nothing(self):
        panel = board(status_every=5.0)
        panel.handle("refresh")
        assert showing(panel) == "departures"


def test_frame_is_the_configured_size():
    frame = board().frame(FRAME)
    assert frame.size == (256, 64)
    assert frame.mode == "RGB"
