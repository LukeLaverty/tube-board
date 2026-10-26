"""
The status board as plain text, for `status --text`.
"""

from ..models import LineStatus
from ..selection import rows_for

NAME_COLUMN = 24


def status_lines(
    statuses: list[LineStatus], selected: list[str] | None = None
) -> list[str]:
    lines = []
    for status in rows_for(statuses, selected):
        lines.append(f"{status.name:{NAME_COLUMN}s} {status.description}")
        if status.reason:
            lines.append(f"{'':{NAME_COLUMN}s} {status.reason}")
    return lines
