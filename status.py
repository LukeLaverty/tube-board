#!/usr/bin/env python3
"""
Lists each selected line with its status and disruption reasons. Runs as its
own window, and also renders one-shot PNGs (--once) so this script can be used
by a cron job.
"""

import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from tube_board import status as board
from tube_board.config import CONFIG_FILE, id_list, load_config
from tube_board.status.schedule import day_index, validate


def parse_args() -> Namespace:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_FILE)
    parser.add_argument(
        "--lines",
        metavar="IDS",
        help="comma-separated line IDs, ignoring any schedule",
    )
    parser.add_argument(
        "--day",
        metavar="DAY",
        help="render as if it were this day, e.g. mon (for testing)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="use canned data instead of the live API",
    )
    parser.add_argument(
        "--once",
        metavar="PATH",
        help="fetch once, save the board as a PNG, and exit",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="print the board to the terminal and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    try:
        validate(config["status"]["schedule"])
        weekday = day_index(args.day) if args.day else None
    except ValueError as exception:
        sys.exit(f"Config error: {exception}")

    override = id_list(args.lines) if args.lines is not None else None
    fetch = board.make_fetcher(args.mock)

    if args.text:
        selected = board.selection_for(config, override, weekday)
        board.print_status_text(fetch(selected), selected)
    elif args.once:
        board.render_once(config, args.once, fetch, override, weekday)
    else:
        board.run(config, fetch, override, weekday)


if __name__ == "__main__":
    sys.exit(main())
