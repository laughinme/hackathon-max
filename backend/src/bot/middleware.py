"""Dependency injection for bot handlers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

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
