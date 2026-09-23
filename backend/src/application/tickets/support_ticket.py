"""A neighbour presses "me too" on a ticket card in the house chat."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from application.errors import TicketNotFoundError
from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.chat_card import queue_card_refresh
from application.tickets.dto import TicketView


@dataclass(frozen=True, slots=True)
class SupportResult:
    ticket: TicketView
    counted: bool


class SupportTicket:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, queries: TicketQueries, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._clock = clock

    async def execute(self, ticket_id: UUID, user_id: int) -> SupportResult:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            ticket = await uow.tickets.get(ticket_id)
            if ticket is None:
                raise TicketNotFoundError()
            counted = ticket.support(user_id, now)
            if counted:
                await uow.tickets.save(ticket)
                await queue_card_refresh(uow, ticket, now)
                await uow.commit()

        view = await self._queries.get(ticket_id, now)
        assert view is not None
        return SupportResult(view, counted)
