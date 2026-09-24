"""Texts of the dispatcher side of the bot (fallback to the mini-app)."""

from __future__ import annotations

from application.tickets.dto import TicketView
from bot.presenters import (
    STATUS_LABELS,
    category_title,
    format_moment,
    urgency_label,
)


def queue(company_name: str, tickets: list[TicketView]) -> str:
    overdue = sum(ticket.is_overdue for ticket in tickets)
    if not tickets:
        return f"🗂 <b>Очередь заявок · {company_name}</b>\n\nОткрытых заявок нет."
    return (
        f"🗂 <b>Очередь заявок · {company_name}</b>\n\n"
        f"Открыто: {len(tickets)}, просрочено: {overdue}.\n"
        "Сверху — ближайший срок. 🚨 — срок истёк, ⚠️ — авария."
    )


def card(ticket: TicketView) -> str:
    overdue = "\n🚨 <b>Срок устранения истёк</b>" if ticket.is_overdue else ""
    history = "\n".join(
        f"• {format_moment(event.at)} — {STATUS_LABELS[event.status]}"
        + (f": {event.comment}" if event.comment else "")
        for event in ticket.events
    )
    return (
        f"🧾 <b>Заявка № {ticket.number}</b>\n"
        f"{ticket.building_address}\n\n"
        f"Статус: {STATUS_LABELS[ticket.status]}{overdue}\n"
        f"Категория: {category_title(ticket.category_code)}, "
        f"{urgency_label(ticket.is_emergency)}\n"
        f"Срок устранения: до <b>{format_moment(ticket.resolve_by)}</b>\n"
        f"<i>{ticket.deadline_basis}</i>\n"
        f"{_neighbours(ticket)}{_photos(ticket)}\n"
        f"<b>Описание</b>\n{ticket.description}\n\n"
        f"<b>История</b>\n{history}"
    )


def _photos(ticket: TicketView) -> str:
    return f"📷 Фото от жителя: {len(ticket.photos)}\n" if ticket.photos else ""


def _neighbours(ticket: TicketView) -> str:
    if not ticket.supporters_count:
        return ""
    source = " · из домового чата" if ticket.chat_card_mid else ""
    return f"👥 Касается ещё соседей: <b>{ticket.supporters_count}</b>{source}\n"


def ask_comment(status_label: str) -> str:
    return (
        f"Новый статус: {status_label}\n\n"
        "Напишите комментарий для жителя (например, «мастер придёт завтра "
        "к 10:00») или нажмите «Без комментария»."
    )


def not_a_dispatcher() -> str:
    return "Эта функция доступна диспетчеру управляющей организации."
