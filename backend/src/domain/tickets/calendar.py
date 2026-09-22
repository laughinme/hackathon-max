"""Working-day arithmetic for deadlines expressed in working days.

Holidays follow Labour Code art. 112 (fixed dates). Government transfers of
days off for a specific year are NOT applied yet — verify against the
official production calendar before relying on 1/3/10-day deadlines
(docs/DATA.md §2).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

FIXED_HOLIDAYS: frozenset[tuple[int, int]] = frozenset(
    {
        (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8),
        (2, 23), (3, 8), (5, 1), (5, 9), (6, 12), (11, 4),
    }
)  # fmt: skip


def is_working_day(day: date) -> bool:
    return day.weekday() < 5 and (day.month, day.day) not in FIXED_HOLIDAYS


def add_working_days(start: datetime, days: int) -> datetime:
    """End of the `days`-th working day after `start` (in start's timezone)."""

    current = start.date()
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if is_working_day(current):
            remaining -= 1
    return datetime.combine(current, datetime.max.time(), tzinfo=start.tzinfo)
