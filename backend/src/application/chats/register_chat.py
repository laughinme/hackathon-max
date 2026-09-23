"""The bot was added to or removed from a group chat."""

from __future__ import annotations

from application.ports.clock import Clock
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.chats.entities import HouseChat


class RegisterChat:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, chat_id: int, added_by: int) -> HouseChat:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            chat = await uow.chats.get(chat_id)
            if chat is None:
                chat = HouseChat(chat_id=chat_id, added_by=added_by, added_at=now)
            else:
                chat.rejoin(added_by, now)
            await uow.chats.save(chat)
            await uow.commit()
        return chat


class LeaveChat:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, chat_id: int) -> None:
        async with self._uow_factory() as uow:
            chat = await uow.chats.get(chat_id)
            if chat is None:
                return
            chat.leave()
            await uow.chats.save(chat)
            await uow.commit()
