#!/usr/bin/env python3
"""
Live London Underground boards, from TfL Open Data.

    python -m tube_board departures   a platform "next train indicator"
    python -m tube_board status       a panel of line statuses
    python -m tube_board search       look up a station's stop ID
"""

import sys
from argparse import (
    SUPPRESS,
    ArgumentParser,
    Namespace,
    RawDescriptionHelpFormatter,
)
from pathlib import Path

from . import runner
from .config import id_list, load_config
from .selection import configured_lines, day_index, selection_for, validate
from .sources import snapshot_source, status_fetcher

SCREENSHOT_FRAMES = 90  # ~3 seconds at 30 FPS.
SCREENSHOT_DT = 1 / 30


def add_departures_args(departures: ArgumentParser) -> None:
    departures.add_argument("--config", type=Path, help="path to a config.toml")
    departures.add_argument(
        "--lines",
        metavar="IDS",
        help="comma-separated line IDs to show, or 'all'",
    )
    departures.add_argument(
        "--platforms",
        help="comma-separated platform substrings, or 'all'",
    )
    departures.add_argument(
        "--rows", type=int, help="how many departures to list"
    )
    departures.add_argument(
        "--status-every",
        type=float,
        metavar="SECONDS",
        help="seconds between line status passes (0 means never"
        " which hands the bottom row back to the ticker)",
    )
    departures.add_argument(
        "--mock",
        action="store_true",
        help="use canned data instead of the live API",
    )
    departures.add_argument(
        "--screenshot",
        metavar="PATH",
        help="render 3 seconds headless, save a PNG, and exit",
    )
    # The old spelling of `search`, hidden from --help.
    departures.add_argument("--search", metavar="QUERY", help=SUPPRESS)


def add_status_args(status: ArgumentParser) -> None:
    status.add_argument("--config", type=Path, help="path to a config.toml")
    status.add_argument(
        "--lines",
        metavar="IDS",
        help="comma-separated line IDs, ignoring any schedule",
    )
    status.add_argument(
        "--day",
        metavar="DAY",
        help="render as if it were this day, e.g. mon (for testing)",
    )
    status.add_argument(
        "--mock",
        action="store_true",
        help="use canned data instead of the live API",
    )
    status.add_argument(
        "--once",
        metavar="PATH",
        help="fetch once, save the board as a PNG, and exit",
    )
    status.add_argument(
        "--text",
        action="store_true",
        help="print the board to the terminal and exit",
    )


def add_search_args(search: ArgumentParser) -> None:
    search.add_argument("query", help="part of a station name")


COMMANDS = {
    "departures": (add_departures_args, "the LED departure board"),
    "status": (add_status_args, "the service information board"),
    "search": (add_search_args, "look up a station's stop ID"),
}


def parse_args(
    argv: list[str] | None = None,
    command: str | None = None,
    prog: str = "python -m tube_board",
) -> Namespace:
    """
    Parse the whole CLI, or only `command`'s flags for the departures.py and
    status.py shorthands.
    """
    if command:
        add_args, help_text = COMMANDS[command]
        parser = ArgumentParser(prog=prog, description=help_text)
        add_args(parser)
        args = parser.parse_args(argv)
        args.command = command
        return args

    parser = ArgumentParser(
        prog=prog,
        description=__doc__,
        formatter_class=RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (add_args, help_text) in COMMANDS.items():
        add_args(sub.add_parser(name, help=help_text))
    return parser.parse_args(argv)


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
    # 0 means never, so compare against None.
    if args.status_every is not None:
        config["display"]["status_every"] = args.status_every


def run_search(query: str) -> int:
    from .config import load_app_key
    from .sources.tfl import TflClient

    stops = TflClient(load_app_key()).search_stations(query)
    if not stops:
        print(f"No stations found for {query!r}")
        return 1
    for stop in stops:
        print(f"{stop['id']:12s} {stop['name']}  ({', '.join(stop['modes'])})")
    print("\nPut the ID you want into config.toml under [station]")
    return 0


def run_departures(config: dict, args: Namespace) -> int:
    # Deferred so `search` and `status` don't import Pygame.
    from .boards.panel import PanelBoard
    from .drivers.window import Window

    apply_overrides(config, args)
    display = config["display"]
    headless = bool(args.screenshot)

    status_modes = None
    if not args.mock:
        # Imported here so `--mock` doesn't need requests.
        from .sources.tfl import modes_for

        status_modes = modes_for(configured_lines(config))

    get_snapshot, stop = snapshot_source(
        config,
        args.mock,
        wait_for_data=headless,
        status_modes=status_modes,
    )
    try:
        board = PanelBoard(
            config,
            get_snapshot,
            selection=(lambda: selection_for(config))
            if display.get("status_follows_schedule")
            else None,
            wall_clock=not headless,
        )
        with Window(
            *board.size,
            int(display["scale"]),
            title=f"Tube Board - {config['station']['name']}",
            dot_matrix=True,
            headless=headless,
        ) as driver:
            runner.run(
                board,
                driver,
                fps=int(display["fps"]),
                frames=SCREENSHOT_FRAMES if headless else None,
                fixed_dt=SCREENSHOT_DT if headless else None,
            )
            if args.screenshot:
                driver.save(args.screenshot)
                print(f"Saved {args.screenshot}")
    finally:
        stop()
    return 0


def run_status(config: dict, args: Namespace) -> int:
    try:
        weekday = day_index(args.day) if args.day else None
    except ValueError as exception:
        sys.exit(f"Config error: {exception}")

    override = id_list(args.lines) if args.lines is not None else None
    fetch = status_fetcher(args.mock)

    if args.text:
        from .render.text import status_lines

        selected = selection_for(config, override, weekday)
        for line in status_lines(fetch(selected), selected):
            print(line)
        return 0

    from .boards.paper import StatusPaperBoard

    board = StatusPaperBoard(config, fetch, override=override, weekday=weekday)

    if args.once:
        from .drivers.png import PngFile

        with PngFile() as driver:
            runner.run(board, driver, fps=0, frames=1)
            if not board.fetched:
                # Fail loudly rather than overwrite a good image with an empty
                # board.
                print(
                    f"Could not reach the API; {args.once} not written",
                    file=sys.stderr,
                )
                return 1
            driver.save(args.once)
        print(f"Saved {args.once}")
        return 0

    from .drivers.window import Window

    with Window(
        *board.size, title="Tube Board - Service Information"
    ) as driver:
        runner.run(board, driver, fps=10)
    return 0


def main(
    argv: list[str] | None = None,
    command: str | None = None,
    prog: str = "python -m tube_board",
) -> int:
    args = parse_args(argv, command, prog)
    if args.command == "search":
        return run_search(args.query)
    if args.command == "departures" and args.search:
        return run_search(args.search)

    try:
        config = load_config(args.config)
        # Both boards can follow the schedule, so check it before either
        # starts rather than at the first status pass.
        validate(config["status"]["schedule"])
    except (FileNotFoundError, ValueError) as exception:
        sys.exit(f"Config error: {exception}")
    if args.command == "departures":
        return run_departures(config, args)
    return run_status(config, args)


if __name__ == "__main__":
    sys.exit(main())
