"""Unit of Work over one SQLAlchemy session and transaction."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.db.housing_repository import SqlHousingRepository
from infrastructure.db.outbox import SqlOutbox
from infrastructure.db.repositories import SqlTicketRepository


class SqlUnitOfWork:
    tickets: SqlTicketRepository
    housing: SqlHousingRepository
    outbox: SqlOutbox

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.tickets = SqlTicketRepository(self._session)
        self.housing = SqlHousingRepository(self._session)
        self.outbox = SqlOutbox(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            await self._session.rollback()  # no-op after a successful commit
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()
