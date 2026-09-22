"""Texts for onboarding, the main menu and roles."""

from __future__ import annotations

from application.housing.identity import Identity

QR_HINT = (
    "В реальном доме ссылка на бота с кодом дома висит в подъезде в виде "
    "QR-кода, выбирать ничего не нужно."
)


def greeting(name: str | None, identity: Identity) -> str:
    who = f", {name}" if name else ""
    lines = [
        f"👋 Здравствуйте{who}!",
        "",
        "Я регистрирую заявки по дому: вы описываете проблему обычными словами, "
        "а я определяю, кто за неё отвечает, и показываю срок устранения по "
        "нормативу и статус заявки.",
    ]
    if identity.residency:
        home = identity.residency
        lines += ["", f"🏠 Ваш дом: {home.address}", f"УО: {home.company_name}"]
    if identity.dispatcher:
        lines += ["", f"🧑‍💼 Вы диспетчер: {identity.dispatcher.company_name}"]
    lines += ["", "Выберите действие 👇"]
    return "\n".join(lines)


def choose_building(pending_problem: bool) -> str:
    intro = (
        "Чтобы оформить заявку, выберите дом."
        if pending_problem
        else "🏠 <b>Выберите ваш дом</b>"
    )
    return (
        f"{intro}\n\n"
        "Для проверки доступны демонстрационные дома управляющей организации "
        "«Комфорт» в Пскове.\n\n"
        f"<i>{QR_HINT}</i>"
    )


def building_bound(address: str) -> str:
    return f"✅ Дом сохранён: {address}"


def building_not_found() -> str:
    return "🤔 Не нашёл такой дом. Выберите дом из списка."


def demo_dispatcher_enabled(company_name: str) -> str:
    return (
        f"🧑‍💼 <b>Вы диспетчер УО «{company_name}» (демо)</b>\n\n"
        "Откройте «Очередь заявок»: там заявки всех домов УО, отсортированные "
        "по сроку. Меняйте статусы — житель получит уведомление."
    )
