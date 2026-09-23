"""SQLAlchemy implementation of the ticket repository port."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from domain.tickets.entities import ANONYMOUS_REPORTER, Ticket
from domain.tickets.state_machine import OPEN
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

    async def detach_reporter(self, reporter_id: int) -> int:
        result = await self._session.execute(
            update(TicketRow)
            .where(TicketRow.reporter_id == reporter_id)
            .values(reporter_id=ANONYMOUS_REPORTER)
        )
        return cast(CursorResult[Any], result).rowcount or 0

    async def list_overdue_unnotified(self, now: datetime, limit: int) -> list[Ticket]:
        rows = await self._session.scalars(
            select(TicketRow)
            .where(
                TicketRow.status.in_([status.value for status in OPEN]),
                TicketRow.resolve_by < now,
                TicketRow.overdue_notified_at.is_(None),
            )
            .order_by(TicketRow.resolve_by)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return [ticket_to_domain(row) for row in rows]
