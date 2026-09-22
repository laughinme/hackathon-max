"""How domain values look in the chat: labels, emoji, dates.

Kept out of the domain on purpose: the aggregate knows nothing about UI.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from domain.tickets.catalog import get_category
from domain.tickets.enums import ResponsibleParty, TicketStatus

DISPLAY_TIMEZONE = ZoneInfo("Europe/Moscow")

STATUS_LABELS: dict[TicketStatus, str] = {
    TicketStatus.REGISTERED: "📥 Зарегистрирована",
    TicketStatus.ACKNOWLEDGED: "👀 Принята УО",
    TicketStatus.IN_PROGRESS: "🔧 В работе",
    TicketStatus.DONE: "🏁 Выполнена, ждёт подтверждения",
    TicketStatus.CONFIRMED: "✅ Закрыта",
    TicketStatus.REJECTED: "⛔️ Отклонена",
}

STATUS_EMOJI: dict[TicketStatus, str] = {
    status: label.split(" ", 1)[0] for status, label in STATUS_LABELS.items()
}

PARTY_LABELS: dict[ResponsibleParty, str] = {
    ResponsibleParty.MANAGEMENT_COMPANY: "Управляющая организация",
    ResponsibleParty.RESOURCE_SUPPLIER: "Ресурсоснабжающая организация",
    ResponsibleParty.CAPITAL_REPAIR_OPERATOR: "Региональный оператор капремонта",
    ResponsibleParty.MUNICIPALITY: "Администрация муниципалитета",
    ResponsibleParty.OWNER: "Собственник помещения",
}


def format_moment(moment: datetime) -> str:
    return moment.astimezone(DISPLAY_TIMEZONE).strftime("%d.%m %H:%M")


def category_title(code: str) -> str:
    return get_category(code).title


def urgency_label(is_emergency: bool) -> str:
    return "⚠️ аварийная" if is_emergency else "плановая"


def short_description(text: str, limit: int = 28) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 1].rstrip() + "…"
