"""Find tickets that just passed their legal deadline and tell people once."""

from __future__ import annotations

from application.ports.clock import Clock
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.overdue_notice import queue_overdue_notices

BATCH_SIZE = 50


class DetectOverdueTickets:
    """Marks and notifications are written in one transaction, so a crash never
    notifies twice or loses a ticket."""

    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self) -> int:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            tickets = await uow.tickets.list_overdue_unnotified(now, BATCH_SIZE)
            for ticket in tickets:
                if ticket.mark_overdue_notified(now):
                    await uow.tickets.save(ticket)
                    await queue_overdue_notices(uow, ticket, now)
            await uow.commit()
        return len(tickets)
