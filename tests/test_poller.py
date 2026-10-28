"""
The background poller: per-feed errors and backing off a failing API.
"""

import requests

from tube_board.sources.tfl import BACKOFF_MAX, Poller, backoff


class TestBackoff:
    def test_a_healthy_feed_keeps_its_interval(self):
        assert backoff(10.0, 0) == 10.0

    def test_doubles_with_each_failure_in_a_row(self):
        assert [backoff(10.0, n) for n in (1, 2, 3)] == [20.0, 40.0, 80.0]

    def test_is_capped(self):
        assert backoff(10.0, 20) == BACKOFF_MAX

    def test_never_polls_faster_than_the_interval(self):
        # An interval already past the cap is left as it is.
        assert backoff(600.0, 3) == 600.0


class FlakyClient:
    def __init__(self):
        self.arrivals_up = True
        self.status_up = True

    def arrivals(self, stop_id):
        if not self.arrivals_up:
            raise requests.ConnectionError("arrivals down")
        return []

    def line_status(self, modes):
        if not self.status_up:
            raise requests.ConnectionError("status down")
        return []


def test_one_feed_recovering_does_not_hide_the_other_failing():
    client = FlakyClient()
    poller = Poller(client, "940GZZLUKSX")
    client.arrivals_up = False
    poller._fetch_arrivals()
    poller._fetch_status()

    snapshot = poller.snapshot()
    assert snapshot.arrivals_error == "arrivals down"
    assert snapshot.status_error is None


def test_a_success_clears_the_feed_error_and_its_failures():
    client = FlakyClient()
    poller = Poller(client, "940GZZLUKSX")
    client.status_up = False
    poller._fetch_status()
    poller._fetch_status()
    assert poller._status_failures == 2

    client.status_up = True
    poller._fetch_status()
    assert poller._status_failures == 0
    assert poller.snapshot().status_error is None


def test_stop_waits_for_the_thread_to_finish():
    poller = Poller(FlakyClient(), "940GZZLUKSX")
    poller.start()
    poller.stop()
    assert not poller._thread.is_alive()


def test_stop_before_start_is_harmless():
    Poller(FlakyClient(), "940GZZLUKSX").stop()
