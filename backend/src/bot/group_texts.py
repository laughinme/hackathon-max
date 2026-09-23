"""Messages the bot posts in house chats: short, one screen, no jargon."""

from __future__ import annotations

from application.tickets.dto import TicketView
from bot.presenters import PARTY_LABELS, STATUS_LABELS, category_title, format_moment
from domain.housing.entities import Building
from domain.tickets.catalog import get_category
from domain.tickets.sla import Deadlines
from domain.tickets.state_machine import OPEN


def welcome() -> str:
    return (
        "👋 <b>Здравствуйте, соседи! Я «Домовой».</b>\n\n"
        "Помогаю оформлять заявки в управляющую организацию прямо из этого "
        "чата: называю нормативный срок, показываю, сколько соседей это "
        "касается, и слежу, чтобы срок не сорвали.\n\n"
        "<b>Выберите дом этого чата:</b>\n\n"
        "<i>Чтобы я замечал жалобы в переписке, сделайте меня администратором "
        "с правом «Читать все сообщения».</i>"
    )


def bound(building: Building, private_link: str) -> str:
    return (
        f"✅ <b>Чат привязан к дому:</b> {building.address}\n\n"
        "Пишите о проблемах как обычно — «нет воды», «лифт стоит», «в подъезде "
        "темно». Я предложу оформить заявку, а соседи смогут нажать "
        "«👍 Я тоже».\n\n"
        f"Жильцам без этого чата: {private_link}"
    )


def hint(category_code: str, deadlines: Deadlines, ask_emergency: bool) -> str:
    category = get_category(category_code)
    question = (
        "\n\n⚠️ <b>Это авария?</b> Угроза людям или имуществу, нет воды или "
        "тепла во всём доме? От ответа зависит срок."
        if ask_emergency
        else ""
    )
    return (
        f"🤖 Похоже на проблему в доме: <b>{category.emoji} {category.title}</b>\n"
        f"Оформлю заявку в УО. Срок устранения — до "
        f"<b>{format_moment(deadlines.resolve_by)}</b>\n"
        f"<i>{deadlines.legal_basis}</i>{question}"
    )


def known_problem(ticket: TicketView) -> str:
    return (
        f"👀 Об этом уже сообщили: <b>заявка № {ticket.number}</b> · "
        f"{category_title(ticket.category_code)}\n"
        f"Статус: {STATUS_LABELS[ticket.status]} · срок до "
        f"{format_moment(ticket.resolve_by)}\n\n"
        "Если у вас то же самое — нажмите «👍 Я тоже»: УО увидит, скольких "
        "соседей это касается."
    )


def card(ticket: TicketView) -> str:
    category = get_category(ticket.category_code)
    lines = [
        f"🧾 <b>Заявка № {ticket.number}</b> · {category.emoji} {category.title}",
        f"📍 {ticket.building_address}",
        f"Отвечает: {PARTY_LABELS[ticket.responsible_party]}",
    ]
    if ticket.status in OPEN:
        overdue = " — 🚨 <b>просрочено</b>" if ticket.is_overdue else ""
        lines.append(f"Срок устранения: до {format_moment(ticket.resolve_by)}{overdue}")
    lines.append(f"Статус: {STATUS_LABELS[ticket.status]}")
    if ticket.supporters_count:
        lines.append(f"👥 Поддержали соседи: {ticket.supporters_count}")
    if ticket.escalated_at:
        lines.append("📨 Готовится жалоба в жилищную инспекцию")
    lines.append(f"\n<i>{ticket.deadline_basis}</i>")
    if ticket.status in OPEN:
        lines.append("Та же проблема? Нажмите «👍 Я тоже».")
    return "\n".join(lines)
