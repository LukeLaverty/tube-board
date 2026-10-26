#!/usr/bin/env python3
"""
The service information board.

    python status.py --once /tmp/status.png

Shorthand for `python -m tube_board status`.
"""

import sys

from tube_board.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], "status", "python status.py"))
