"""Buttons under the bot's messages in house chats."""

from __future__ import annotations

from uuid import UUID

from maxapi.enums.intent import Intent
from maxapi.types.attachments.buttons import CallbackButton, LinkButton
from maxapi.types.attachments.buttons.attachment_button import AttachmentButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from application.tickets.dto import TicketView
from bot import callbacks
from domain.housing.entities import Building
from domain.tickets.state_machine import OPEN


def buildings(options: list[Building]) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    for building in options:
        builder.row(
            CallbackButton(
                text=f"🏠 {building.address}",
                payload=callbacks.pack(callbacks.GROUP_BUILDING, building.code),
            )
        )
    return builder.as_markup()


def hint(hint_id: UUID, ask_emergency: bool) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    if ask_emergency:
        builder.row(
            CallbackButton(
                text="⚠️ Да, авария",
                payload=callbacks.pack(callbacks.GROUP_FILE, f"{hint_id}:e"),
                intent=Intent.NEGATIVE,
            ),
            CallbackButton(
                text="📝 Нет, обычная",
                payload=callbacks.pack(callbacks.GROUP_FILE, f"{hint_id}:n"),
            ),
        )
    else:
        builder.row(
            CallbackButton(
                text="📝 Оформить заявку",
                payload=callbacks.pack(callbacks.GROUP_FILE, f"{hint_id}:a"),
                intent=Intent.POSITIVE,
            )
        )
    builder.row(
        CallbackButton(
            text="✖️ Не нужно",
            payload=callbacks.pack(callbacks.GROUP_DROP, str(hint_id)),
        )
    )
    return builder.as_markup()


def card(ticket: TicketView, bot_link: str) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    if ticket.status in OPEN:
        count = f" · {ticket.supporters_count}" if ticket.supporters_count else ""
        builder.row(
            CallbackButton(
                text=f"👍 Я тоже{count}",
                payload=callbacks.pack(callbacks.GROUP_SUPPORT, str(ticket.id)),
            )
        )
    builder.row(
        LinkButton(
            text="🔔 Следить в личке",
            url=f"{bot_link}?start=t_{ticket.id}",
        )
    )
    return builder.as_markup()
