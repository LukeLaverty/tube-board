"""
Which lines a status board shows, and in what order.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from .models import LineStatus, line_sort_key

if TYPE_CHECKING:
    # Only for annotations: `config.py` imports this module to check schedules.
    from .config import Config

DAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_GROUPS = {
    "all": set(range(7)),
    "daily": set(range(7)),
    "everyday": set(range(7)),
    "weekday": set(range(5)),
    "weekdays": set(range(5)),
    "weekend": {5, 6},
    "weekends": {5, 6},
}


def day_index(name: str) -> int:
    key = name.strip().lower()[:3]
    try:
        return DAY_NAMES.index(key)
    except ValueError:
        raise ValueError(
            f"Unknown day {name!r}; use mon, tue ... sun"
        ) from None


def parse_days(spec: str) -> set[int]:
    text = spec.strip().lower()
    if text in DAY_GROUPS:
        return set(DAY_GROUPS[text])
    days: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if part in DAY_GROUPS:
            days |= DAY_GROUPS[part]
        elif "-" in part:
            start, _, end = part.partition("-")
            first, last = day_index(start), day_index(end)
            # A backwards range wraps through the end of the week, so
            # "fri-mon" means Friday, Saturday, Sunday, Monday.
            if first <= last:
                days.update(range(first, last + 1))
            else:
                days.update([*range(first, 7), *range(0, last + 1)])
        else:
            days.add(day_index(part))
    if not days:
        raise ValueError(f"No days given in {spec!r}")
    return days


def validate(schedule: list[dict]) -> None:
    """
    Raise on a malformed rule, so a typo surfaces at startup.
    """
    for rule in schedule:
        parse_days(str(rule.get("days", "")))


def lines_for(
    schedule: list[dict],
    fallback: list[str],
    weekday: int | None = None,
) -> list[str]:
    """
    First matching rule wins; its empty `lines` list means every line.
    """
    if weekday is None:
        weekday = datetime.now().weekday()
    for rule in schedule:
        if weekday in parse_days(str(rule.get("days", ""))):
            return [
                str(line).strip().lower()
                for line in rule.get("lines", [])
                if str(line).strip()
            ]
    return fallback


def selection_for(
    config: "Config",
    override: list[str] | None = None,
    weekday: int | None = None,
) -> list[str]:
    """
    A caller's override beats the day's schedule, which beats [status] lines.
    """
    if override is not None:
        return override
    fallback = [
        line.strip().lower() for line in config.status.lines if line.strip()
    ]
    return lines_for(config.status.schedule, fallback, weekday)


def configured_lines(config: "Config") -> list[str]:
    """
    Every line named anywhere in [status], so one fetch covers any day.
    """
    names = list(config.status.lines)
    for rule in config.status.schedule:
        names.extend(rule.get("lines", []))
    ordered = {}
    for name in names:
        if key := str(name).strip().lower():
            ordered.setdefault(key)
    return list(ordered)


def rows_for(
    statuses: list[LineStatus], selected: list[str] | None = None
) -> list[LineStatus]:
    """
    The lines a status board shows, in the order it shows them.
    """
    if selected:
        # An explicit selection sets the running order too.
        position = {line: i for i, line in enumerate(selected)}
        return sorted(
            (status for status in statuses if status.line_id in position),
            key=lambda s: position[s.line_id],
        )
    return sorted(statuses, key=lambda s: line_sort_key(s.line_id))
