"""Тексты экранов бота.

Держим их в одном месте: так проще править формулировки и видеть
весь пользовательский путь целиком.
"""

from __future__ import annotations

from domain.tickets.entities import Request

MOCK_NOTE = "⚠️ Демо-режим: обращение регистрируется в модельной системе УК."


def greeting(name: str | None = None) -> str:
    """Приветственный экран."""

    who = f", {name}" if name else ""
    return (
        f"👋 Здравствуйте{who}!\n\n"
        "Я помогаю жителям доводить проблемы по дому до результата: "
        "вы описываете ситуацию обычными словами, а я определяю "
        "ответственного, формирую обращение в управляющую организацию "
        "и показываю статус.\n\n"
        "Выберите действие 👇"
    )


def choose_category() -> str:
    """Экран быстрых сценариев."""

    return (
        "📝 <b>Новое обращение</b>\n\n"
        "Выберите, что случилось. Это просто быстрые сценарии — "
        "если ничего не подходит, <b>напишите проблему своими словами "
        "прямо в чат</b>, я разберусь сам."
    )


def collecting_started(category_title: str, question: str) -> str:
    """Первый уточняющий вопрос после выбора категории."""

    return (
        f"📝 <b>Новое обращение · {category_title}</b>\n\n"
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


def draft(text: str, responsible: str, urgency: str) -> str:
    """Экран черновика обращения."""

    return (
        "📄 <b>Черновик обращения</b>\n\n"
        f"{text}\n\n"
        "———\n"
        f"Ответственный: {responsible}\n"
        f"Срочность: {urgency}\n\n"
        "Если что-то смущает — <b>напишите в чат, что поправить</b>, "
        "и я перепишу текст. Когда всё верно, нажмите «Готово»."
    )


def submitting() -> str:
    """Промежуточный экран отправки."""

    return "⏳ Отправляю обращение в управляющую организацию…"


def submitted(request: Request) -> str:
    """Экран успешной отправки."""

    external = (
        f"Номер в системе УК: {request.external_id}\n" if request.external_id else ""
    )
    note = f"\n{MOCK_NOTE}" if request.is_mock_integration else ""
    return (
        "✅ <b>Обращение отправлено</b>\n\n"
        f"Номер: <b>{request.number}</b>\n"
        f"{external}"
        f"Статус: {request.status.label}\n"
        f"Ответственный: {request.responsible}\n\n"
        "Обращение сохранено в разделе «Мои обращения». "
        f"Об изменении статуса я сообщу в этот чат.{note}"
    )


def submit_failed(error: str) -> str:
    """Экран ошибки отправки — из него всегда есть выход."""

    return (
        "⚠️ <b>Не удалось отправить обращение</b>\n\n"
        f"Причина: {error}\n\n"
        "Черновик сохранён — можно повторить отправку."
    )


def empty_requests() -> str:
    """Пустой список обращений."""

    return (
        "📂 <b>Мои обращения</b>\n\n"
        "Пока здесь пусто. Создайте первое обращение — "
        "оно появится в этом списке со статусом."
    )


def requests_list(count: int) -> str:
    """Список обращений."""

    return (
        "📂 <b>Мои обращения</b>\n\n"
        f"Всего обращений: {count}. "
        "Выберите обращение, чтобы посмотреть статус и текст."
    )


def request_card(request: Request) -> str:
    """Карточка одного обращения."""

    history = "\n".join(
        f"• {event.at:%d.%m %H:%M} — {event.status.label}" for event in request.history
    )
    external = (
        f"Номер в системе УК: {request.external_id}\n" if request.external_id else ""
    )
    note = f"\n\n{MOCK_NOTE}" if request.is_mock_integration else ""

    return (
        f"📄 <b>Обращение {request.number}</b>\n\n"
        f"Статус: {request.status.label}\n"
        f"Категория: {request.title}\n"
        f"Ответственный: {request.responsible}\n"
        f"Срочность: {request.urgency}\n"
        f"{external}"
        f"Создано: {request.created_at:%d.%m.%Y %H:%M}\n\n"
        "<b>Текст обращения</b>\n"
        f"{request.text}\n\n"
        "<b>История статусов</b>\n"
        f"{history}"
        f"{note}"
    )


def status_changed(request: Request) -> str:
    """Уведомление об изменении статуса."""

    return (
        f"🔔 <b>Обращение {request.number}</b>\n"
        f"Новый статус: {request.status.label}\n\n"
        "Подробности — в разделе «Мои обращения»."
    )


def request_not_found() -> str:
    """Обращение не найдено (например, бот перезапущен)."""

    return (
        "🤔 Не нашёл это обращение. "
        "Возможно, бот был перезапущен и демо-данные сброшены.\n\n"
        "Откройте список обращений заново."
    )


def unknown_message() -> str:
    """Свободный текст вне сценария."""

    return (
        "Я вас понял, но сейчас не в сценарии обращения.\n\n"
        "Нажмите «Создать обращение» — и опишите проблему "
        "своими словами, я помогу оформить её в УК."
    )


def error_occurred() -> str:
    """Экран непредвиденной ошибки."""

    return (
        "⚠️ Что-то пошло не так, но я уже в порядке.\n\n"
        "Попробуйте ещё раз — сценарий можно начать заново."
    )
