"""PostgreSQL inbox: one row per processed update key (INSERT ... ON CONFLICT)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.db.models import InboxRow


class SqlInbox:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def register(self, key: str, now: datetime) -> bool:
        async with self._session_factory() as session, session.begin():
            result = await session.execute(
                insert(InboxRow)
                .values(dedup_key=key, received_at=now)
                .on_conflict_do_nothing(index_elements=[InboxRow.dedup_key])
                .returning(InboxRow.dedup_key)
            )
            return result.scalar_one_or_none() is not None

    async def purge(self, older_than: datetime) -> int:
        async with self._session_factory() as session, session.begin():
            result = await session.execute(
                delete(InboxRow).where(InboxRow.received_at < older_than)
            )
            return cast(CursorResult[Any], result).rowcount or 0
