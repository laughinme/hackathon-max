"""Read-side use cases for a resident's own tickets."""

from __future__ import annotations

from uuid import UUID

from application.errors import TicketNotFoundError
from application.ports.clock import Clock
from application.ports.tickets import UnitOfWorkFactory
from application.tickets.dto import TicketView, to_view


class ListReporterTickets:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, reporter_id: int) -> list[TicketView]:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            tickets = await uow.tickets.list_by_reporter(reporter_id)
        return [to_view(ticket, now) for ticket in tickets]


class GetReporterTicket:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, ticket_id: UUID, reporter_id: int) -> TicketView:
        async with self._uow_factory() as uow:
            ticket = await uow.tickets.get(ticket_id)
        if ticket is None or ticket.reporter_id != reporter_id:
            raise TicketNotFoundError()
        return to_view(ticket, self._clock.now())
