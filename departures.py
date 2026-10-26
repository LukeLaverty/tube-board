#!/usr/bin/env python3
"""
The departure board.

    python departures.py --mock

Shorthand for `python -m tube_board departures`.
"""

import sys

from tube_board.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], "departures", "python departures.py"))
