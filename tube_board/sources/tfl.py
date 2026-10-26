"""
TfL Unified API client and background poller.
"""

import threading
import time

import requests

from ..models import (
    NON_TFL_LINE_IDS,
    TFL_LINE_IDS,
    Departure,
    LineStatus,
    Snapshot,
)

BASE_URL = "https://api.tfl.gov.uk"
STATUS_MODES = "tube,elizabeth-line,overground,dlr,tram"
# National Rail operators (notably Thameslink) are a separate mode.
NATIONAL_RAIL_MODE = "national-rail"

_STATION_SUFFIXES = (
    " Underground Station",
    " DLR Station",
    " Rail Station",
    " Station",
)

# NaPTAN ID prefixes for stops the arrivals endpoint accepts.
_ARRIVALS_CAPABLE_PREFIXES = ("940G", "910G")


def wanted(mode: str, line_id: str) -> bool:
    """
    National Rail comes as a whole mode of about 25 operators; keep only
    Thameslink.
    """
    return mode != NATIONAL_RAIL_MODE or line_id in NON_TFL_LINE_IDS


def modes_for(selected: list[str]) -> str:
    """
    Add National Rail when the selection names a non-TfL line, or is empty
    (meaning every line).
    """
    if not selected or any(line not in TFL_LINE_IDS for line in selected):
        return f"{STATUS_MODES},{NATIONAL_RAIL_MODE}"
    return STATUS_MODES


def clean_station_name(name: str) -> str:
    for suffix in _STATION_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


class TflClient:
    def __init__(self, app_key: str | None = None, timeout: float = 10.0):
        self._session = requests.Session()
        self._base_params = {"app_key": app_key} if app_key else {}
        self._timeout = timeout

    def _get(self, path: str, **params):
        response = self._session.get(
            f"{BASE_URL}{path}",
            params={**self._base_params, **params},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()

    def line_status(self, modes: str = STATUS_MODES) -> list[LineStatus]:
        raw = self._get(f"/Line/Mode/{modes}/Status")
        statuses = []
        for line in raw:
            line_statuses = line.get("lineStatuses") or []
            if not line_statuses:
                continue
            mode = line.get("modeName", "")
            if not wanted(mode, line.get("id", "")):
                continue
            # A line can carry several concurrent statuses; report the worst
            # (lower severity number = more severe).
            worst = min(
                line_statuses,
                key=lambda s: s.get("statusSeverity", 10),
            )
            # National Rail puts a disruption link where TfL writes prose.
            reason = (
                None
                if mode == NATIONAL_RAIL_MODE
                else (worst.get("reason") or "").strip() or None
            )
            statuses.append(
                LineStatus(
                    line_id=line.get("id", ""),
                    name=line.get("name", ""),
                    mode=mode,
                    severity=worst.get("statusSeverity", 10),
                    description=worst.get(
                        "statusSeverityDescription", "Unknown"
                    ),
                    reason=reason,
                )
            )
        return statuses

    def arrivals(self, stop_id: str) -> list[Departure]:
        raw = self._get(f"/StopPoint/{stop_id}/Arrivals")
        departures = [
            Departure(
                line_id=prediction.get("lineId", ""),
                line_name=prediction.get("lineName", ""),
                platform=prediction.get("platformName", ""),
                towards=(prediction.get("towards") or "").strip()
                or clean_station_name(prediction.get("destinationName", "")),
                destination=clean_station_name(
                    prediction.get("destinationName", "")
                ),
                seconds=int(prediction.get("timeToStation", 0)),
                current_location=prediction.get("currentLocation", ""),
            )
            for prediction in raw
            if wanted(
                prediction.get("modeName", ""),
                prediction.get("lineId", ""),
            )
        ]
        departures.sort(key=lambda d: d.seconds)
        return departures

    def search_stations(self, query: str) -> list[dict]:
        """
        Resolve a station name to arrivals-capable stop IDs (940G.../910G...).
        """
        found: dict[str, dict] = {}
        matches = self._get(
            f"/StopPoint/Search/{query}", modes=STATUS_MODES
        ).get("matches", [])
        for match in matches[:8]:
            for stop in self._expand_match(match):
                found.setdefault(stop["id"], stop)
        return list(found.values())

    def _expand_match(self, match: dict) -> list[dict]:
        stop_id = match.get("id", "")
        if stop_id.startswith(_ARRIVALS_CAPABLE_PREFIXES):
            return [
                {
                    "id": stop_id,
                    "name": match.get("name", stop_id),
                    "modes": match.get("modes", []),
                }
            ]
        try:
            detail = self._get(f"/StopPoint/{stop_id}")
        except requests.RequestException:
            return []
        wanted_modes = set(STATUS_MODES.split(","))
        out: list[dict] = []

        def walk(node: dict) -> None:
            naptan = node.get("naptanId") or node.get("id") or ""
            modes = node.get("modes") or []
            if (
                naptan.startswith(_ARRIVALS_CAPABLE_PREFIXES)
                and set(modes) & wanted_modes
            ):
                out.append(
                    {
                        "id": naptan,
                        "name": node.get("commonName", naptan),
                        "modes": modes,
                    }
                )
            for child in node.get("children") or []:
                walk(child)

        walk(detail)
        return out


class Poller:
    """
    Background thread keeping arrivals and line status fresh.
    """

    def __init__(
        self,
        client: TflClient,
        stop_id: str,
        arrivals_every: float = 10.0,
        status_every: float = 90.0,
        status_modes: str = STATUS_MODES,
    ):
        self._client = client
        self._stop_id = stop_id
        self._arrivals_every = arrivals_every
        self._status_every = status_every
        self._status_modes = status_modes
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._departures: list[Departure] = []
        self._statuses: list[LineStatus] = []
        self._arrivals_at = 0.0
        self._status_at = 0.0
        self._error: str | None = None

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def snapshot(self) -> Snapshot:
        now = time.monotonic()
        with self._lock:
            return Snapshot(
                departures=list(self._departures),
                statuses=list(self._statuses),
                arrivals_age=now - self._arrivals_at
                if self._arrivals_at
                else float("inf"),
                status_age=now - self._status_at
                if self._status_at
                else float("inf"),
                error=self._error,
            )

    def _run(self) -> None:
        next_arrivals = 0.0
        next_status = 0.0
        while not self._stop_event.is_set():
            now = time.monotonic()
            if now >= next_arrivals:
                next_arrivals = now + self._arrivals_every
                self._fetch_arrivals()
            if now >= next_status:
                next_status = now + self._status_every
                self._fetch_status()
            self._stop_event.wait(0.5)

    def _fetch_arrivals(self) -> None:
        try:
            departures = self._client.arrivals(self._stop_id)
        except requests.RequestException as exc:
            with self._lock:
                self._error = str(exc)
            return
        with self._lock:
            self._departures = departures
            self._arrivals_at = time.monotonic()
            self._error = None

    def _fetch_status(self) -> None:
        try:
            statuses = self._client.line_status(self._status_modes)
        except requests.RequestException as exc:
            with self._lock:
                self._error = str(exc)
            return
        with self._lock:
            self._statuses = statuses
            self._status_at = time.monotonic()
            self._error = None
