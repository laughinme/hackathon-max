"""Link a house chat to its building."""

from __future__ import annotations

from dataclasses import dataclass

from application.ports.clock import Clock
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.chats.entities import HouseChat
from domain.housing.entities import Building
from domain.housing.exceptions import BuildingNotFoundError


@dataclass(frozen=True, slots=True)
class ChatBinding:
    chat: HouseChat
    building: Building


class BindChat:
    """Anyone in the chat may pick the building the first time; afterwards only
    the person who added the bot can change it, so a prank cannot move it."""

    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(
        self, chat_id: int, building_code: str, user_id: int
    ) -> ChatBinding:
        async with self._uow_factory() as uow:
            building = await uow.housing.get_building_by_code(building_code)
            if building is None:
                raise BuildingNotFoundError()
            chat = await uow.chats.get(chat_id)
            if chat is None:
                chat = HouseChat(chat_id, added_by=user_id, added_at=self._clock.now())
            elif (
                chat.building_id not in (None, building.id) and user_id != chat.added_by
            ):
                current = await uow.housing.get_building(chat.building_id)
                if current is not None:
                    return ChatBinding(chat, current)
            chat.bind(building.id)
            await uow.chats.save(chat)
            await uow.commit()
        return ChatBinding(chat, building)


class GetChatBinding:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, chat_id: int) -> ChatBinding | None:
        async with self._uow_factory() as uow:
            chat = await uow.chats.get(chat_id)
            if chat is None or not chat.is_bound or chat.building_id is None:
                return None
            building = await uow.housing.get_building(chat.building_id)
        return ChatBinding(chat, building) if building else None
