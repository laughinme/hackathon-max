"""House pulse: how the company handles this building's tickets lately.

Numbers residents can check themselves: how many problems, how many are
still open or overdue, what share was fixed within the legal deadline. The
pressure of a public, factual summary is the point; no ratings, no opinions.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.tickets.dto import TicketView
from domain.tickets.enums import TicketStatus
from domain.tickets.state_machine import OPEN

PERIOD = timedelta(days=30)
FIXED = (TicketStatus.DONE, TicketStatus.CONFIRMED)


@dataclass(frozen=True, slots=True)
class Pulse:
    period_days: int
    total: int
    open: int
    overdue: int
    fixed: int
    fixed_on_time: int
    average_fix_hours: float | None
    top_categories: tuple[tuple[str, int], ...]
    neighbours_joined: int

    @property
    def on_time_share(self) -> float | None:
        return self.fixed_on_time / self.fixed if self.fixed else None


def _fixed_at(ticket: TicketView) -> datetime | None:
    return next((e.at for e in ticket.events if e.status in FIXED), None)


def compute_pulse(tickets: list[TicketView], period: timedelta = PERIOD) -> Pulse:
    fixed_times = [(t, at) for t in tickets if (at := _fixed_at(t)) is not None]
    hours = [(at - t.created_at).total_seconds() / 3600 for t, at in fixed_times]
    return Pulse(
        period_days=period.days,
        total=len(tickets),
        open=sum(t.status in OPEN for t in tickets),
        overdue=sum(t.is_overdue for t in tickets),
        fixed=len(fixed_times),
        fixed_on_time=sum(at <= t.resolve_by for t, at in fixed_times),
        average_fix_hours=sum(hours) / len(hours) if hours else None,
        top_categories=tuple(Counter(t.category_code for t in tickets).most_common(3)),
        neighbours_joined=sum(t.supporters_count for t in tickets),
    )


class GetBuildingPulse:
    def __init__(self, queries: TicketQueries, clock: Clock) -> None:
        self._queries = queries
        self._clock = clock

    async def execute(self, building_id: UUID) -> Pulse:
        now = self._clock.now()
        tickets = await self._queries.list_for_building(building_id, now - PERIOD, now)
        return compute_pulse(tickets)
