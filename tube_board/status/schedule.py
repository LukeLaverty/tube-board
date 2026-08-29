"""
Day-of-week rules for which lines the status display shows.
"""

from datetime import datetime

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
