"""Inline-клавиатуры бота.

Вся навигация строится на callback-кнопках: экран не «дописывается»
новым сообщением, а перерисовывается на месте (см. app/screen.py).
"""

from __future__ import annotations

from uuid import UUID

from maxapi.enums.intent import Intent
from maxapi.types.attachments.buttons import CallbackButton
from maxapi.types.attachments.buttons.attachment_button import (
    AttachmentButton,
)
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from application.tickets.dto import TicketView
from bot import callbacks
from bot.presenters import STATUS_EMOJI, short_description
from domain.tickets.catalog import CATEGORIES, OTHER


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
            text="✅ Отправить",
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
            text="📂 Мои заявки",
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


def requests_list(tickets: list[TicketView]) -> AttachmentButton:
    """One button per ticket, newest first."""

    builder = InlineKeyboardBuilder()
    for ticket in tickets:
        builder.row(
            CallbackButton(
                text=(
                    f"{STATUS_EMOJI[ticket.status]} № {ticket.number} — "
                    f"{short_description(ticket.description)}"
                ),
                payload=callbacks.pack(callbacks.MY_ITEM, str(ticket.id)),
            )
        )
    builder.row(
        CallbackButton(
            text="📝 Сообщить о проблеме",
            payload=callbacks.pack(callbacks.NEW),
        )
    )
    builder.row(_back_to_menu())
    return builder.as_markup()


def emergency_question() -> AttachmentButton:
    """Resident confirms or denies an emergency when the classifier is unsure."""

    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="⚠️ Да, это авария",
            payload=callbacks.pack(callbacks.EMERGENCY, "yes"),
            intent=Intent.NEGATIVE,
        ),
        CallbackButton(
            text="Нет, не срочно",
            payload=callbacks.pack(callbacks.EMERGENCY, "no"),
        ),
    )
    builder.row(_back_to_menu())
    return builder.as_markup()


def request_card(ticket: TicketView | None = None) -> AttachmentButton:
    """Карточка обращения; у просроченной — жалоба в жилинспекцию."""

    builder = InlineKeyboardBuilder()
    if ticket is not None and ticket.can_escalate:
        builder.row(escalate_button(ticket.id))
    builder.row(
        CallbackButton(
            text="⬅️ К списку заявок",
            payload=callbacks.pack(callbacks.MY_LIST),
        )
    )
    builder.row(_back_to_menu())
    return builder.as_markup()


def escalate_button(ticket_id: UUID) -> CallbackButton:
    return CallbackButton(
        text="📄 Жалоба в жилинспекцию",
        payload=callbacks.pack(callbacks.ESCALATE, str(ticket_id)),
        intent=Intent.NEGATIVE,
    )


def menu_only() -> AttachmentButton:
    """Single "main menu" button: a safe way out of any error screen."""

    builder = InlineKeyboardBuilder()
    builder.row(_back_to_menu())
    return builder.as_markup()


def _back_to_menu() -> CallbackButton:
    return CallbackButton(
        text="🏠 Главное меню",
        payload=callbacks.pack(callbacks.MENU),
    )
