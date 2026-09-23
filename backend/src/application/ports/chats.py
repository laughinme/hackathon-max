"""Persistence port for house chats and the bot's hints in them."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from domain.chats.entities import ChatHint, HouseChat


class ChatRepository(Protocol):
    async def get(self, chat_id: int) -> HouseChat | None: ...

    async def save(self, chat: HouseChat) -> None: ...

    async def add_hint(self, hint: ChatHint) -> None: ...

    async def get_hint(self, hint_id: UUID) -> ChatHint | None:
        """Locked for the transaction: concurrent "file it" presses serialise."""
        ...

    async def save_hint(self, hint: ChatHint) -> None: ...
