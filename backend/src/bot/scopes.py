"""Router filters: dialog flows never see house-chat updates and vice versa.

A house chat gets its own short messages; the step-by-step screens of the
dialog would answer every neighbour's message with a menu.
"""

from __future__ import annotations

from typing import Any

from maxapi.enums.chat_type import ChatType
from maxapi.filters.filter import BaseFilter
from maxapi.types.updates.bot_added import BotAdded
from maxapi.types.updates.bot_removed import BotRemoved


def chat_type(event: Any) -> ChatType | None:
    message = getattr(event, "message", None)
    recipient = getattr(message, "recipient", None)
    return getattr(recipient, "chat_type", None)


class DialogScope(BaseFilter):
    async def __call__(self, event: Any) -> bool:
        if isinstance(event, BotAdded | BotRemoved):
            return False
        kind = chat_type(event)
        return kind is None or kind == ChatType.DIALOG


class GroupScope(BaseFilter):
    async def __call__(self, event: Any) -> bool:
        if isinstance(event, BotAdded | BotRemoved):
            return not event.is_channel
        return chat_type(event) == ChatType.CHAT
