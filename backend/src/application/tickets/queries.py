"""Read-side use cases with access control."""

from __future__ import annotations

from uuid import UUID

from application.errors import TicketNotFoundError
from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.dto import TicketView
from domain.housing.exceptions import NotADispatcherError

QUEUE_LIMIT = 50


class ListReporterTickets:
    def __init__(self, queries: TicketQueries, clock: Clock) -> None:
        self._queries = queries
        self._clock = clock

    async def execute(self, reporter_id: int) -> list[TicketView]:
        return await self._queries.list_for_reporter(reporter_id, self._clock.now())


class GetTicketForUser:
    """The reporter or a dispatcher of the managing company may see a ticket."""

    def __init__(
        self, uow_factory: UnitOfWorkFactory, queries: TicketQueries, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._clock = clock

    async def execute(self, ticket_id: UUID, user_id: int) -> TicketView:
        ticket = await self._queries.get(ticket_id, self._clock.now())
        if ticket is None:
            raise TicketNotFoundError()
        if ticket.reporter_id == user_id:
            return ticket
        async with self._uow_factory() as uow:
            dispatcher = await uow.housing.get_dispatcher(user_id)
        if dispatcher is None or dispatcher.company_id != ticket.company_id:
            raise TicketNotFoundError()  # do not reveal that the ticket exists
        return ticket


class ListDispatcherQueue:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, queries: TicketQueries, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._clock = clock

    async def execute(
        self, user_id: int, *, open_only: bool = True, limit: int = QUEUE_LIMIT
    ) -> list[TicketView]:
        async with self._uow_factory() as uow:
            dispatcher = await uow.housing.get_dispatcher(user_id)
        if dispatcher is None:
            raise NotADispatcherError()
        return await self._queries.list_for_company(
            dispatcher.company_id,
            self._clock.now(),
            open_only=open_only,
            limit=min(limit, QUEUE_LIMIT),
        )
