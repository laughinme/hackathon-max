"""Свободный ввод вне сценария и обработка непредвиденных ошибок.

Chat-first: если житель просто написал о проблеме, не нажимая кнопок,
мы сразу начинаем сценарий обращения — это основной способ входа.
"""

from __future__ import annotations

import logging

from maxapi import ExceptionTypeFilter, Router
from maxapi.context import MemoryContext
from maxapi.types import ErrorEvent
from maxapi.types.updates import MessageCreated

from bot import keyboards, texts
from bot.handlers.create import CATEGORY, TURNS, _analyze_and_render
from bot.screen import render, user_message_text
from bot.states import CreateRequest
from domain.tickets.catalog import guess_category

logger = logging.getLogger(__name__)
router = Router(router_id="fallback")

#: Слишком короткий текст не считаем описанием проблемы.
MIN_PROBLEM_LENGTH = 8


@router.message_created()
async def on_free_text(event: MessageCreated, context: MemoryContext) -> None:
    """Пользователь описал проблему своими словами вне сценария."""

    text = user_message_text(event)
    if not text or text.startswith("/"):
        return

    if len(text) < MIN_PROBLEM_LENGTH:
        await render(event, context, texts.unknown_message(), keyboards.main_menu())
        return

    category = guess_category(text)
    await context.update_data(
        **{
            CATEGORY: category.code,
            TURNS: [{"role": "user", "text": text}],
        }
    )
    await context.set_state(CreateRequest.collecting)
    await _analyze_and_render(event, context)


@router.errors(ExceptionTypeFilter(Exception))
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
        await render(update, context, texts.error_occurred(), keyboards.main_menu())
    except Exception:  # noqa: BLE001 - запасной путь, молчим
        logger.warning("Не удалось показать экран ошибки")
