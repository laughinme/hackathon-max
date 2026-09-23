"""Keyboards of the dispatcher side and of resident notifications."""

from __future__ import annotations

from uuid import UUID

from maxapi.enums.intent import Intent
from maxapi.types.attachments.buttons import CallbackButton
from maxapi.types.attachments.buttons.attachment_button import AttachmentButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from application.tickets.dto import TicketView
from bot import callbacks, keyboards
from bot.presenters import format_moment, short_description
from domain.tickets.enums import ActorRole, TicketStatus
from domain.tickets.state_machine import next_statuses

QUEUE_BUTTONS = 10
ACTION_LABELS: dict[TicketStatus, str] = {
    TicketStatus.ACKNOWLEDGED: "👀 Принять",
    TicketStatus.IN_PROGRESS: "🔧 В работу",
    TicketStatus.DONE: "🏁 Выполнено",
    TicketStatus.REJECTED: "⛔️ Отклонить",
}


def _menu() -> CallbackButton:
    return CallbackButton(
        text="🏠 Главное меню", payload=callbacks.pack(callbacks.MENU)
    )


def _queue_mark(ticket: TicketView) -> str:
    if ticket.is_overdue:
        return "🚨"
    return "⚠️" if ticket.is_emergency else "⏰"


def _crowd(ticket: TicketView) -> str:
    return f"👥{ticket.supporters_count + 1} " if ticket.supporters_count else ""


def queue(tickets: list[TicketView]) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    for ticket in tickets[:QUEUE_BUTTONS]:
        builder.row(
            CallbackButton(
                text=(
                    f"{_queue_mark(ticket)} до {format_moment(ticket.resolve_by)} · "
                    f"{_crowd(ticket)}{short_description(ticket.description, 24)}"
                ),
                payload=callbacks.pack(callbacks.QUEUE_ITEM, str(ticket.id)),
            )
        )
    builder.row(
        CallbackButton(text="🔄 Обновить", payload=callbacks.pack(callbacks.QUEUE))
    )
    builder.row(_menu())
    return builder.as_markup()


def card(ticket: TicketView) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    actions = [
        CallbackButton(
            text=ACTION_LABELS[status],
            payload=callbacks.pack(callbacks.QUEUE_SET, f"{ticket.id}:{status.value}"),
        )
        for status in next_statuses(ticket.status, ActorRole.DISPATCHER)
    ]
    for index in range(0, len(actions), 2):
        builder.row(*actions[index : index + 2])
    builder.row(
        CallbackButton(text="⬅️ К очереди", payload=callbacks.pack(callbacks.QUEUE))
    )
    builder.row(_menu())
    return builder.as_markup()


def comment_prompt(ticket_id: UUID) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="Без комментария",
            payload=callbacks.pack(callbacks.QUEUE_SKIP_COMMENT),
            intent=Intent.POSITIVE,
        )
    )
    builder.row(
        CallbackButton(
            text="Отмена", payload=callbacks.pack(callbacks.QUEUE_ITEM, str(ticket_id))
        )
    )
    return builder.as_markup()


def notification(ticket_id: UUID, status: TicketStatus) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    if status is TicketStatus.DONE:
        builder.row(
            CallbackButton(
                text="✅ Да, всё работает",
                payload=callbacks.pack(callbacks.CONFIRM_FIXED, str(ticket_id)),
                intent=Intent.POSITIVE,
            ),
            CallbackButton(
                text="❌ Нет, не починили",
                payload=callbacks.pack(callbacks.CONFIRM_REOPEN, str(ticket_id)),
                intent=Intent.NEGATIVE,
            ),
        )
    builder.row(
        CallbackButton(
            text="📄 Открыть заявку",
            payload=callbacks.pack(callbacks.MY_ITEM, str(ticket_id)),
        )
    )
    return builder.as_markup()


def overdue_for_resident(ticket_id: UUID) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(keyboards.escalate_button(ticket_id))
    builder.row(
        CallbackButton(
            text="📄 Открыть заявку",
            payload=callbacks.pack(callbacks.MY_ITEM, str(ticket_id)),
        )
    )
    return builder.as_markup()


def overdue_for_dispatcher(ticket_id: UUID) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="🗂 Открыть карточку",
            payload=callbacks.pack(callbacks.QUEUE_ITEM, str(ticket_id)),
        )
    )
    return builder.as_markup()
