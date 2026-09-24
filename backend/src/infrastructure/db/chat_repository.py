"""SQLAlchemy implementation of the chat repository port."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.chats.entities import ChatHint, HouseChat
from domain.tickets.entities import TicketPhoto
from infrastructure.db.models import ChatHintRow, HouseChatRow


def _chat(row: HouseChatRow) -> HouseChat:
    return HouseChat(
        chat_id=row.chat_id,
        added_by=row.added_by,
        added_at=row.added_at,
        building_id=row.building_id,
        is_active=row.is_active,
    )


def _hint(row: ChatHintRow) -> ChatHint:
    return ChatHint(
        id=row.id,
        chat_id=row.chat_id,
        message_mid=row.message_mid,
        author_id=row.author_id,
        text=row.text,
        category_code=row.category_code,
        is_emergency=row.is_emergency,
        needs_emergency_confirmation=row.needs_emergency_confirmation,
        created_at=row.created_at,
        ticket_id=row.ticket_id,
        photos=tuple(TicketPhoto(**photo) for photo in row.photos or []),
    )


class SqlChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, chat_id: int) -> HouseChat | None:
        row = await self._session.get(HouseChatRow, chat_id)
        return _chat(row) if row else None

    async def save(self, chat: HouseChat) -> None:
        await self._session.merge(
            HouseChatRow(
                chat_id=chat.chat_id,
                building_id=chat.building_id,
                added_by=chat.added_by,
                added_at=chat.added_at,
                is_active=chat.is_active,
            )
        )

    async def add_hint(self, hint: ChatHint) -> None:
        self._session.add(
            ChatHintRow(
                id=hint.id,
                chat_id=hint.chat_id,
                message_mid=hint.message_mid,
                author_id=hint.author_id,
                text=hint.text,
                category_code=hint.category_code,
                is_emergency=hint.is_emergency,
                needs_emergency_confirmation=hint.needs_emergency_confirmation,
                created_at=hint.created_at,
                ticket_id=hint.ticket_id,
                photos=[{"token": p.token, "url": p.url} for p in hint.photos],
            )
        )

    async def get_hint(self, hint_id: UUID) -> ChatHint | None:
        row = await self._session.scalar(
            select(ChatHintRow).where(ChatHintRow.id == hint_id).with_for_update()
        )
        return _hint(row) if row else None

    async def save_hint(self, hint: ChatHint) -> None:
        row = await self._session.get(ChatHintRow, hint.id)
        if row is None:
            raise LookupError(f"Hint {hint.id} is not persisted")
        row.ticket_id = hint.ticket_id
