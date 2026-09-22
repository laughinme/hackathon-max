"""Last-resort error handler for every router of the dispatcher.

Registered on the dispatcher itself (see `app.main.build_dispatcher`), so an
exception in any handler is logged and the user gets a way back to the menu.
"""

from __future__ import annotations

import logging

from maxapi.types import ErrorEvent

from bot import keyboards, texts
from bot.screen import render

logger = logging.getLogger(__name__)


async def on_error(event: ErrorEvent) -> None:
    """Логируем сбой и не оставляем пользователя без ответа."""

    logger.exception(
        "Ошибка обработки события %s",
        type(event.update).__name__,
        exc_info=event.exception,
    )

    context = getattr(event, "context", None)
    update = event.update
    if context is None or update is None:
        return

    try:
        await render(update, context, texts.error_occurred(), keyboards.menu_only())
    except Exception:  # noqa: BLE001 - запасной путь, молчим
        logger.warning("Не удалось показать экран ошибки")
