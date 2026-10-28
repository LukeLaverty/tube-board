"""
Data sources: the live TfL API or mock data. Imports are deferred so --mock
doesn't need requests.
"""

import time
from collections.abc import Callable

from ..config import Config, load_app_key
from ..models import LineStatus, Snapshot

# Seconds a headless render waits for the first live poll.
FIRST_POLL_WAIT = 15


def status_fetcher(
    mock: bool = False,
) -> Callable[[list[str]], list[LineStatus]]:
    """
    A callable taking the selected line IDs and returning their statuses.
    """
    if mock:
        from .mock import mock_statuses

        return lambda selected: mock_statuses()

    from .tfl import TflClient, modes_for

    client = TflClient(load_app_key())
    return lambda selected: client.line_status(modes_for(selected))


def snapshot_source(
    config: Config,
    mock: bool = False,
    *,
    wait_for_data: bool = False,
    status_modes: str | None = None,
) -> tuple[Callable[[], Snapshot], Callable[[], None]]:
    """
    Returns `(get_snapshot, stop)`. `stop` does nothing in mock mode.
    """
    if mock:
        from .mock import mock_snapshot

        return mock_snapshot, lambda: None

    from .tfl import STATUS_MODES, Poller, TflClient

    poller = Poller(
        TflClient(load_app_key()),
        config.station.id,
        arrivals_every=config.refresh.arrivals_seconds,
        status_every=config.refresh.status_seconds,
        status_modes=status_modes or STATUS_MODES,
    )
    poller.start()
    if wait_for_data:
        deadline = time.time() + FIRST_POLL_WAIT
        while time.time() < deadline:
            snapshot = poller.snapshot()
            if snapshot.departures and snapshot.statuses:
                break
            time.sleep(0.2)
    return poller.snapshot, poller.stop
