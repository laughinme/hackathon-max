"""Навигация «одним сообщением».

Главный UX-принцип бота: при переходах экран не засоряет чат новыми
сообщениями, а перерисовывается на месте.

- нажатие inline-кнопки → редактируем сообщение через callback-ответ;
- сообщение пользователя → удаляем прежний экран и присылаем новый под
  сообщением пользователя. Редактировать старый экран здесь нельзя: он
  уезжает вверх, и ответ бота оказывается выше того, на что он отвечает.
  Удалить сообщение пользователя в диалоге бот не может (API разрешает
  удалять только свои), поэтому экран «следует» за пользователем.

Если старый экран удалить не удалось (уже удалён, сбой API), это не
мешает: новый экран всё равно отправляется — тупиков нет.
"""

from __future__ import annotations

import logging

from maxapi import Bot
from maxapi.context.base import BaseContext
from maxapi.exceptions import MaxError
from maxapi.types.attachments.buttons.attachment_button import (
    AttachmentButton,
)
from maxapi.types.updates.base_update import BaseUpdate
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

logger = logging.getLogger(__name__)

#: Ключ в FSM-контексте, где лежит message_id текущего экрана.
SCREEN_KEY = "screen_message_id"


async def render(
    event: BaseUpdate,
    context: BaseContext,
    text: str,
    keyboard: AttachmentButton,
    *,
    notification: str | None = None,
) -> None:
    """Показывает экран, переиспользуя текущее сообщение бота."""

    if isinstance(event, MessageCallback):
        await _render_callback(event, context, text, keyboard, notification)
        return

    await _render_message(event, context, text, keyboard)


async def _render_callback(
    event: MessageCallback,
    context: BaseContext,
    text: str,
    keyboard: AttachmentButton,
    notification: str | None,
) -> None:
    """Перерисовывает сообщение, на кнопку которого нажали."""

    try:
        await event.edit(
            text=text,
            attachments=[keyboard],
            notification=notification,
        )
    except (MaxError, ValueError) as exc:
        logger.warning("Не удалось отредактировать экран: %s", exc)
        await _send_new(event, context, text, keyboard)
        return

    if event.message is not None and event.message.body is not None:
        await context.update_data(**{SCREEN_KEY: event.message.body.mid})


async def _render_message(
    event: BaseUpdate,
    context: BaseContext,
    text: str,
    keyboard: AttachmentButton,
) -> None:
    """Переносит экран бота под последнее сообщение пользователя."""

    data = await context.get_data()
    message_id = data.get(SCREEN_KEY)

    if message_id:
        bot: Bot = event._ensure_bot()  # noqa: SLF001
        try:
            await bot.delete_message(message_id=message_id)
        except (MaxError, ValueError) as exc:
            logger.info("Прежний экран %s не удалён: %s", message_id, exc)

    await _send_new(event, context, text, keyboard)


async def _send_new(
    event: BaseUpdate,
    context: BaseContext,
    text: str,
    keyboard: AttachmentButton,
) -> None:
    """Отправляет новое сообщение и делает его текущим экраном."""

    bot: Bot = event._ensure_bot()  # noqa: SLF001
    chat_id, user_id = event.get_ids()  # type: ignore[attr-defined]

    sended = await bot.send_message(
        chat_id=chat_id,
        user_id=None if chat_id else user_id,
        text=text,
        attachments=[keyboard],
    )

    if sended is not None and sended.message.body is not None:
        await context.update_data(**{SCREEN_KEY: sended.message.body.mid})


def event_ids(event: BaseUpdate) -> tuple[int | None, int | None]:
    """Возвращает (chat_id, user_id) для любого поддерживаемого события."""

    return event.get_ids()  # type: ignore[attr-defined]


def user_message_text(event: MessageCreated) -> str:
    """Текст сообщения пользователя (пустая строка, если текста нет)."""

    if event.message.body is None or not event.message.body.text:
        return ""
    return event.message.body.text.strip()


def sender_id(event: BaseUpdate) -> int:
    """MAX user id of whoever caused the event (every user event has one)."""

    _, user_id = event.get_ids()  # type: ignore[attr-defined]
    if user_id is None:
        raise ValueError(f"{type(event).__name__} has no sender")
    return int(user_id)
