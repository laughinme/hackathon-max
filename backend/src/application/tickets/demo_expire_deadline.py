"""Demo shortcut: the reporter's deadline passes now instead of in a day.

The overdue notice is queued right here, in the same transaction, instead of
waiting for the next watcher tick: the relay delivers it within seconds and
the checker walks "overdue -> complaint -> PDF" without waiting. The watcher
keeps its calm one-minute interval for real deadlines.
"""

from __future__ import annotations

from uuid import UUID

from application.errors import DemoActionNotAllowedError, TicketNotFoundError
from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.dto import TicketView
from application.tickets.overdue_notice import queue_overdue_notices


class DemoExpireDeadline:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        queries: TicketQueries,
        clock: Clock,
        *,
        demo_mode: bool,
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._clock = clock
        self._demo_mode = demo_mode

    async def execute(self, ticket_id: UUID, user_id: int) -> TicketView:
        if not self._demo_mode:
            raise DemoActionNotAllowedError("Demo mode is off")
        now = self._clock.now()
        async with self._uow_factory() as uow:
            ticket = await uow.tickets.get(ticket_id)
            if ticket is None or ticket.reporter_id != user_id:
                raise TicketNotFoundError()
            company = await uow.housing.get_company(ticket.company_id)
            if company is None or not company.is_demo:
                raise DemoActionNotAllowedError("Only demo companies' tickets")
            if not ticket.is_open or ticket.is_overdue(now):
                raise DemoActionNotAllowedError("Ticket is closed or already overdue")

            ticket.expire_deadline_for_demo(now)
            if ticket.mark_overdue_notified(now):
                await queue_overdue_notices(uow, ticket, now)
            await uow.tickets.save(ticket)
            await uow.commit()

        view = await self._queries.get(ticket_id, now)
        assert view is not None
        return view
