"""Inline-клавиатуры бота.

Вся навигация строится на callback-кнопках: экран не «дописывается»
новым сообщением, а перерисовывается на месте (см. app/screen.py).
"""

from __future__ import annotations

from maxapi.enums.intent import Intent
from maxapi.types.attachments.buttons import CallbackButton
from maxapi.types.attachments.buttons.attachment_button import (
    AttachmentButton,
)
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from app import callbacks
from app.categories import CATEGORIES, OTHER
from app.models import Request


def main_menu() -> AttachmentButton:
    """Главное меню."""

    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="📝 Создать обращение",
            payload=callbacks.pack(callbacks.NEW),
            intent=Intent.POSITIVE,
        )
    )
    builder.row(
        CallbackButton(
            text="📂 Мои обращения",
            payload=callbacks.pack(callbacks.MY_LIST),
        )
    )
    return builder.as_markup()


def categories_menu() -> AttachmentButton:
    """Быстрые сценарии + возврат в меню."""

    builder = InlineKeyboardBuilder()
    for category in CATEGORIES:
        builder.row(
            CallbackButton(
                text=category.button_text,
                payload=callbacks.pack(callbacks.CATEGORY, category.code),
            )
        )
    builder.adjust(2)
    builder.row(
        CallbackButton(
            text=OTHER.button_text,
            payload=callbacks.pack(callbacks.CATEGORY, OTHER.code),
        )
    )
    builder.row(_back_to_menu())
    return builder.as_markup()


def collecting() -> AttachmentButton:
    """Экран уточняющих вопросов: выход из сценария."""

    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="⬅️ К быстрым сценариям",
            payload=callbacks.pack(callbacks.NEW),
        )
    )
    builder.row(_back_to_menu())
    return builder.as_markup()


def draft() -> AttachmentButton:
    """Экран черновика обращения."""

    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="✅ Готово",
            payload=callbacks.pack(callbacks.DRAFT_DONE),
            intent=Intent.POSITIVE,
        )
    )
    builder.row(
        CallbackButton(
            text="🔄 Начать заново",
            payload=callbacks.pack(callbacks.DRAFT_RESTART),
        )
    )
    builder.row(_back_to_menu())
    return builder.as_markup()


def after_submit() -> AttachmentButton:
    """Экран успешной отправки обращения."""

    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="📂 Мои обращения",
            payload=callbacks.pack(callbacks.MY_LIST),
        )
    )
    builder.row(_back_to_menu())
    return builder.as_markup()


def retry_submit() -> AttachmentButton:
    """Экран ошибки отправки: повтор или выход."""

    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="🔁 Повторить отправку",
            payload=callbacks.pack(callbacks.DRAFT_DONE),
            intent=Intent.POSITIVE,
        )
    )
    builder.row(_back_to_menu())
    return builder.as_markup()


def requests_list(requests: list[Request]) -> AttachmentButton:
    """Список обращений — по одной кнопке в строке."""

    builder = InlineKeyboardBuilder()
    for request in requests:
        builder.row(
            CallbackButton(
                text=(
                    f"{request.status.emoji} {request.number} — "
                    f"{request.short_title}"
                ),
                payload=callbacks.pack(callbacks.MY_ITEM, request.id),
            )
        )
    builder.row(
        CallbackButton(
            text="📝 Создать обращение",
            payload=callbacks.pack(callbacks.NEW),
        )
    )
    builder.row(_back_to_menu())
    return builder.as_markup()


def request_card() -> AttachmentButton:
    """Карточка обращения."""

    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="⬅️ К списку обращений",
            payload=callbacks.pack(callbacks.MY_LIST),
        )
    )
    builder.row(_back_to_menu())
    return builder.as_markup()


def _back_to_menu() -> CallbackButton:
    return CallbackButton(
        text="🏠 Главное меню",
        payload=callbacks.pack(callbacks.MENU),
    )
