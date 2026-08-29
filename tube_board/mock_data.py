"""
Canned TfL data for offline development (`--mock`).

The statuses deliberately mix a severe delay, a minor delay and a long reason
string.
"""

from .models import Departure, LineStatus, Snapshot

MOCK_DEPARTURES = [
    Departure(
        "victoria",
        "Victoria",
        "Southbound - Platform 4",
        "Brixton",
        "Brixton",
        20,
        "",
    ),
    Departure(
        "victoria",
        "Victoria",
        "Southbound - Platform 4",
        "Brixton",
        "Brixton",
        130,
        "",
    ),
    Departure(
        "victoria",
        "Victoria",
        "Southbound - Platform 4",
        "Brixton",
        "Brixton",
        340,
        "",
    ),
]

MOCK_STATUSES = [
    LineStatus("bakerloo", "Bakerloo", "tube", 10, "Good Service"),
    LineStatus(
        "central",
        "Central",
        "tube",
        9,
        "Minor Delays",
        "Central Line: Minor delays due to an earlier power failure.",
    ),
    LineStatus("circle", "Circle", "tube", 10, "Good Service"),
    LineStatus("district", "District", "tube", 10, "Good Service"),
    LineStatus(
        "hammersmith-city",
        "Hammersmith & City",
        "tube",
        10,
        "Good Service",
    ),
    LineStatus(
        "jubilee",
        "Jubilee",
        "tube",
        6,
        "Severe Delays",
        "Jubilee Line: Severe delays due to a signal failure at Baker Street. "
        "Tickets are being accepted on local bus routes and on the "
        "Metropolitan line via Wembley Park.",
    ),
    LineStatus("metropolitan", "Metropolitan", "tube", 10, "Good Service"),
    LineStatus("northern", "Northern", "tube", 10, "Good Service"),
    LineStatus("piccadilly", "Piccadilly", "tube", 10, "Good Service"),
    LineStatus("victoria", "Victoria", "tube", 10, "Good Service"),
    LineStatus(
        "waterloo-city",
        "Waterloo & City",
        "tube",
        10,
        "Good Service",
    ),
    LineStatus(
        "elizabeth",
        "Elizabeth line",
        "elizabeth-line",
        10,
        "Good Service",
    ),
    LineStatus("windrush", "Windrush", "overground", 10, "Good Service"),
    LineStatus("dlr", "DLR", "dlr", 10, "Good Service"),
    LineStatus(
        "thameslink",
        "Thameslink",
        "national-rail",
        10,
        "Good Service",
    ),
]


def mock_statuses() -> list[LineStatus]:
    """
    Line statuses, as the status board's fetcher would return them.
    """
    return list(MOCK_STATUSES)


def mock_snapshot() -> Snapshot:
    """
    A poller-shaped snapshot, as the departure board consumes it.
    """
    return Snapshot(
        departures=list(MOCK_DEPARTURES),
        statuses=mock_statuses(),
        arrivals_age=1.0,
        status_age=1.0,
    )
