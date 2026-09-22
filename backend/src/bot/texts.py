"""Тексты экранов бота.

Держим их в одном месте: так проще править формулировки и видеть
весь пользовательский путь целиком.
"""

from __future__ import annotations

from application.tickets.dto import TicketView
from application.tickets.triage_complaint import TriageResult
from bot.presenters import (
    PARTY_LABELS,
    STATUS_LABELS,
    category_title,
    format_moment,
    urgency_label,
)

DEMO_NOTE = (
    "🧪 Тестовый режим: данные демонстрационные, заявка не передаётся "
    "в реальную управляющую организацию."
)


def choose_category() -> str:
    """Экран быстрых сценариев."""

    return (
        "📝 <b>Новая заявка</b>\n\n"
        "Выберите, что случилось. Это просто быстрые сценарии — "
        "если ничего не подходит, <b>напишите проблему своими словами "
        "прямо в чат</b>, я разберусь сам."
    )


def collecting_started(title: str, question: str) -> str:
    """Первый уточняющий вопрос после выбора категории."""

    return (
        f"📝 <b>Новая заявка · {title}</b>\n\n"
        f"{question}\n\n"
        "Напишите ответ сообщением в чат."
    )


def clarifying(question: str, explanation: str) -> str:
    """Уточняющий вопрос по ходу диалога."""

    return (
        "🤖 <b>Уточняю детали</b>\n\n"
        f"{explanation}\n\n"
        f"❓ {question}\n\n"
        "Ответьте сообщением в чат."
    )


def _deadline_lines(resolve_by, react_by, basis: str) -> str:
    react = (
        f"Реакция аварийной службы: до {format_moment(react_by)}\n" if react_by else ""
    )
    return (
        f"{react}"
        f"Срок устранения: до <b>{format_moment(resolve_by)}</b>\n"
        f"<i>Основание: {basis}</i>"
    )


def draft(text: str, triage: TriageResult) -> str:
    """Draft screen with the responsible party and the legal deadline."""

    deadlines = triage.deadlines_preview
    deadline = _deadline_lines(
        deadlines.resolve_by, deadlines.react_by, deadlines.legal_basis
    )
    return (
        "📄 <b>Черновик заявки</b>\n\n"
        f"{text}\n\n"
        "———\n"
        f"Категория: {category_title(triage.category_code)}\n"
        f"Срочность: {urgency_label(triage.is_emergency)}\n"
        f"Отвечает: {PARTY_LABELS[triage.responsibility.party]} "
        f"<i>({triage.responsibility.legal_basis})</i>\n"
        f"{deadline}\n\n"
        "Если что-то не так, <b>напишите в чат, что поправить</b>. "
        "Когда всё верно, нажмите «Отправить»."
    )


def emergency_question() -> str:
    """Asked when the classifier is not sure whether this is an emergency."""

    return (
        "⚠️ <b>Это авария?</b>\n\n"
        "Есть угроза людям или имуществу: топит, искрит, пахнет газом, "
        "кто-то застрял в лифте, нет воды или тепла во всём доме?\n\n"
        "От ответа зависит нормативный срок: аварию устраняют быстрее."
    )


def submitting() -> str:
    return "⏳ Регистрирую заявку…"


def submitted(ticket: TicketView) -> str:
    deadline = _deadline_lines(
        ticket.resolve_by, ticket.react_by, ticket.deadline_basis
    )
    return (
        "✅ <b>Заявка зарегистрирована</b>\n\n"
        f"Номер: <b>№ {ticket.number}</b>\n"
        f"Статус: {STATUS_LABELS[ticket.status]}\n"
        f"Отвечает: {PARTY_LABELS[ticket.responsible_party]}\n"
        f"{deadline}\n\n"
        "Заявка сохранена в разделе «Мои заявки».\n\n"
        f"{DEMO_NOTE}"
    )


def submit_failed() -> str:
    return (
        "⚠️ <b>Не удалось зарегистрировать заявку</b>\n\n"
        "Сервис временно недоступен. Черновик сохранён, повторите отправку."
    )


def empty_requests() -> str:
    return (
        "📂 <b>Мои заявки</b>\n\n"
        "Пока пусто. Создайте первую заявку, и она появится здесь со статусом "
        "и сроком."
    )


def requests_list(count: int) -> str:
    return (
        "📂 <b>Мои заявки</b>\n\n"
        f"Всего: {count}. Выберите заявку, чтобы увидеть статус, срок и историю."
    )


def request_card(ticket: TicketView) -> str:
    history = "\n".join(
        f"• {format_moment(event.at)} — {STATUS_LABELS[event.status]}"
        + (f": {event.comment}" if event.comment else "")
        for event in ticket.events
    )
    overdue = "\n🚨 <b>Срок устранения истёк</b>" if ticket.is_overdue else ""
    deadline = _deadline_lines(
        ticket.resolve_by, ticket.react_by, ticket.deadline_basis
    )
    return (
        f"📄 <b>Заявка № {ticket.number}</b>\n\n"
        f"Статус: {STATUS_LABELS[ticket.status]}{overdue}\n"
        f"Категория: {category_title(ticket.category_code)}\n"
        f"Срочность: {urgency_label(ticket.is_emergency)}\n"
        f"Отвечает: {PARTY_LABELS[ticket.responsible_party]}\n"
        f"{deadline}\n"
        f"Создана: {format_moment(ticket.created_at)}\n\n"
        "<b>Описание</b>\n"
        f"{ticket.description}\n\n"
        "<b>История</b>\n"
        f"{history}\n\n"
        f"{DEMO_NOTE}"
    )


def request_not_found() -> str:
    return "🤔 Не нашёл эту заявку. Откройте список заявок заново."


def unknown_message() -> str:
    """Свободный текст вне сценария."""

    return (
        "Я вас понял, но сейчас не в сценарии заявки.\n\n"
        "Нажмите «Сообщить о проблеме» и опишите её "
        "своими словами, я помогу оформить её в УК."
    )


def error_occurred() -> str:
    """Экран непредвиденной ошибки."""

    return (
        "⚠️ Что-то пошло не так, но я уже в порядке.\n\n"
        "Попробуйте ещё раз — сценарий можно начать заново."
    )
