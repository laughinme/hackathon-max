"""Dependency injection for bot handlers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from maxapi.enums.chat_type import ChatType
from maxapi.filters.middleware import BaseMiddleware

from app.services import Services


class ServicesMiddleware(BaseMiddleware):
    """Exposes the `Services` container as the `services` handler argument."""

    def __init__(self, services: Services) -> None:
        self._services = services

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event_object: Any,
        data: dict[str, Any],
    ) -> Any:
        data["services"] = self._services
        return await handler(event_object, data)


class DialogOnlyMiddleware(BaseMiddleware):
    """Keeps the resident flows out of group chats.

    The screens are built for a 1:1 dialog; in a house chat they would answer
    every neighbour's message with a menu. Group updates are only logged by
    the webhook receiver until the group scenario exists (roadmap step 3).
    """

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event_object: Any,
        data: dict[str, Any],
    ) -> Any:
        message = getattr(event_object, "message", None)
        recipient = getattr(message, "recipient", None)
        chat_type = getattr(recipient, "chat_type", None)
        if chat_type is not None and chat_type != ChatType.DIALOG:
            return None
        return await handler(event_object, data)
