"""House pulse and the responsibility guide, as chat messages."""

from __future__ import annotations

from application.tickets.pulse import Pulse
from domain.tickets.catalog import get_category
from domain.tickets.responsibility_guide import GUIDE


def _hours(value: float) -> str:
    if value < 24:
        return f"{value:.0f} ч"
    return f"{value / 24:.1f} сут".replace(".", ",")


def pulse(address: str, data: Pulse) -> str:
    if data.total == 0:
        return (
            f"📊 <b>Пульс дома</b> · {address}\n\n"
            f"За {data.period_days} дней заявок не было. Тихо — это хорошо."
        )
    lines = [
        f"📊 <b>Пульс дома</b> · {address}",
        f"<i>за {data.period_days} дней</i>\n",
        f"Заявок: <b>{data.total}</b> · открыто {data.open}",
    ]
    if data.overdue:
        lines.append(f"🚨 Просрочено сейчас: <b>{data.overdue}</b>")
    if data.on_time_share is not None:
        lines.append(
            f"✅ Устранено в нормативный срок: <b>{data.on_time_share:.0%}</b> "
            f"({data.fixed_on_time} из {data.fixed})"
        )
    if data.average_fix_hours is not None:
        lines.append(f"⏱ В среднем до устранения: {_hours(data.average_fix_hours)}")
    if data.top_categories:
        top = ", ".join(
            f"{get_category(code).emoji} {get_category(code).title.lower()} — {count}"
            for code, count in data.top_categories
        )
        lines.append(f"Чаще всего: {top}")
    if data.neighbours_joined:
        lines.append(f"👥 Соседи поддержали заявки: {data.neighbours_joined} раз")
    lines.append("\n<i>Считается по заявкам, поданным через «Домового».</i>")
    return "\n".join(lines)


def guide() -> str:
    parts = ["🧭 <b>Кто за что отвечает</b>\n"]
    for entry in GUIDE:
        parts.append(
            f"{entry.emoji} <b>{entry.situation}</b>\n"
            f"→ {entry.who} <i>({entry.basis})</i>\n"
            f"Куда: {entry.where}\n"
        )
    return "\n".join(parts)


def leaflet_caption(address: str) -> str:
    return (
        f"🖨 <b>Листовка для подъезда</b> · {address}\n\n"
        "Распечатайте и повесьте у лифта или на двери: соседи без этого чата "
        "отсканируют QR-код и сразу попадут в бота, уже привязанные к дому."
    )
