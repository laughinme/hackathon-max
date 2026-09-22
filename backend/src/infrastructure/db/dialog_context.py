"""maxapi conversation state stored in PostgreSQL instead of process memory.

A restart or a second replica no longer loses the resident's draft. Passed to
`Dispatcher(storage=PostgresDialogContext, session_factory=...)`.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from maxapi.context.base import BaseContext
from maxapi.context.state_machine import State
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.db.models import DialogStateRow


class PostgresDialogContext(BaseContext):
    def __init__(
        self,
        chat_id: int | None,
        user_id: int | None,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        **kwargs: Any,
    ) -> None:
        super().__init__(chat_id, user_id, **kwargs)
        self._session_factory = session_factory
        self._key = (chat_id or 0, user_id or 0)
        self._lock = asyncio.Lock()

    async def get_data(self) -> dict[str, Any]:
        row = await self._load()
        return dict(row.data) if row else {}

    async def set_data(self, data: dict[str, Any]) -> None:
        async with self._lock:
            state = await self._load_state()
            await self._upsert(state, dict(data))

    async def update_data(self, **kwargs: Any) -> dict[str, Any]:
        async with self._lock:
            row = await self._load()
            data = {**(row.data if row else {}), **kwargs}
            await self._upsert(row.state if row else None, data)
            return dict(data)

    async def set_state(self, state: State | str | None = None) -> None:
        async with self._lock:
            row = await self._load()
            name = str(state) if state is not None else None
            await self._upsert(name, dict(row.data) if row else {})

    async def get_state(self) -> State | str | None:
        return await self._load_state()

    async def clear(self) -> None:
        async with self._lock:
            await self._upsert(None, {})

    async def _load(self) -> DialogStateRow | None:
        async with self._session_factory() as session:
            return await session.get(DialogStateRow, self._key)

    async def _load_state(self) -> str | None:
        row = await self._load()
        return row.state if row else None

    async def _upsert(self, state: str | None, data: dict[str, Any]) -> None:
        now = datetime.now(UTC)
        statement = insert(DialogStateRow).values(
            chat_id=self._key[0],
            user_id=self._key[1],
            state=state,
            data=data,
            updated_at=now,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[DialogStateRow.chat_id, DialogStateRow.user_id],
            set_={"state": state, "data": data, "updated_at": now},
        )
        async with self._session_factory() as session, session.begin():
            await session.execute(statement)
