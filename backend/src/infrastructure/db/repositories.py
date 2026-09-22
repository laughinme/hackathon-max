"""SQLAlchemy implementation of the ticket repository port."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from domain.tickets.entities import Ticket
from infrastructure.db.mappers import apply_ticket, ticket_to_domain, ticket_to_row
from infrastructure.db.models import TICKET_NUMBER_SEQ, TicketRow


class SqlTicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def next_sequence(self) -> int:
        value = await self._session.scalar(TICKET_NUMBER_SEQ.next_value())
        return int(value)

    async def add(self, ticket: Ticket) -> None:
        row = ticket_to_row(ticket)
        self._session.add(row)

    async def get(self, ticket_id: UUID) -> Ticket | None:
        row = await self._session.get(TicketRow, ticket_id)
        return ticket_to_domain(row) if row is not None else None

    async def save(self, ticket: Ticket) -> None:
        row = await self._session.get(TicketRow, ticket.id)
        if row is None:
            raise LookupError(f"Ticket {ticket.id} is not persisted")
        apply_ticket(row, ticket)
