"""SQL read model for tickets: rows joined with building addresses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, case, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.tickets.dto import TicketView, to_view
from domain.tickets.state_machine import OPEN
from infrastructure.db.mappers import ticket_to_domain
from infrastructure.db.models import BuildingRow, TicketRow

OPEN_VALUES = [status.value for status in OPEN]


class SqlTicketQueries:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, ticket_id: UUID, now: datetime) -> TicketView | None:
        views = await self._fetch(self._base().where(TicketRow.id == ticket_id), now)
        return views[0] if views else None

    async def list_for_reporter(
        self, reporter_id: int, now: datetime
    ) -> list[TicketView]:
        return await self._fetch(
            self._base()
            .where(TicketRow.reporter_id == reporter_id)
            .order_by(TicketRow.created_at.desc()),
            now,
        )

    async def list_for_company(
        self, company_id: UUID, now: datetime, *, open_only: bool, limit: int
    ) -> list[TicketView]:
        query = self._base().where(TicketRow.company_id == company_id)
        if open_only:
            query = query.where(TicketRow.status.in_(OPEN_VALUES))
        is_closed = case((TicketRow.status.in_(OPEN_VALUES), 0), else_=1)
        query = query.order_by(is_closed, TicketRow.resolve_by).limit(limit)
        return await self._fetch(query, now)

    @staticmethod
    def _base() -> Select[tuple[TicketRow, str]]:
        return select(TicketRow, BuildingRow.address).join(
            BuildingRow, BuildingRow.id == TicketRow.building_id
        )

    async def _fetch(
        self, query: Select[tuple[TicketRow, str]], now: datetime
    ) -> list[TicketView]:
        async with self._session_factory() as session:
            rows = (await session.execute(query)).all()
            return [
                to_view(ticket_to_domain(row), now, address) for row, address in rows
            ]
