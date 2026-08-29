#!/usr/bin/env python3
"""
A platform "next train indicator" for a dot-matrix panel.
"""

import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from tube_board import departures
from tube_board.config import (
    CONFIG_FILE,
    id_list,
    load_app_key,
    load_config,
)


def print_station_search(client, query: str) -> None:
    stops = client.search_stations(query)
    if not stops:
        print(f"No stations found for {query!r}")
        return
    for stop in stops:
        print(f"{stop['id']:12s} {stop['name']}  ({', '.join(stop['modes'])})")
    print("\nPut the ID you want into config.toml under [station]")


def parse_args() -> Namespace:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_FILE)
    parser.add_argument(
        "--lines",
        metavar="IDS",
        help="comma-separated line IDs to show, or 'all'",
    )
    parser.add_argument(
        "--platforms",
        help="comma-separated platform substrings, or 'all'",
    )
    parser.add_argument("--rows", type=int, help="how many departures to list")
    parser.add_argument(
        "--status-every",
        type=float,
        metavar="SECONDS",
        help="seconds between line status passes (0 means never"
        " which hands the bottom row back to the ticker)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="use canned data instead of the live API",
    )
    parser.add_argument(
        "--screenshot",
        metavar="PATH",
        help="render 3 seconds headless, save a PNG, and exit",
    )
    parser.add_argument(
        "--search",
        metavar="QUERY",
        help="look up a station's stop ID and exit",
    )
    return parser.parse_args()


def apply_overrides(config: dict, args: Namespace) -> None:
    station = config["station"]
    for value, key in (
        (args.lines, "lines"),
        (args.platforms, "platforms"),
    ):
        if value is not None:
            station[key] = (
                [] if value.strip().lower() == "all" else id_list(value)
            )
    if args.rows:
        station["max_rows"] = args.rows
    # Explicitly compared to None, 0 is a meaningful value, not "unset".
    if args.status_every is not None:
        config["display"]["status_every"] = args.status_every


def main() -> None:
    args = parse_args()

    if args.search:
        from tube_board.tfl import TflClient

        print_station_search(TflClient(load_app_key()), args.search)
        return

    config = load_config(args.config)
    apply_overrides(config, args)
    departures.run(config, mock=args.mock, screenshot=args.screenshot)


if __name__ == "__main__":
    sys.exit(main())
