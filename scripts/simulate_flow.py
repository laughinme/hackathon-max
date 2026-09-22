"""Оффлайн-прогон основного сценария бота без обращения к API MAX.

Скрипт подменяет транспорт фейковым «чатом» и прогоняет CJM целиком:
приветствие → быстрый сценарий → уточнение → черновик → правка →
отправка в УК → «Мои обращения» → карточка обращения → меню.

Дополнительно проверяется ключевое требование к навигации:
все экраны показываются в ОДНОМ и том же сообщении (edit in place).

Запуск:  python -m scripts.simulate_flow
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

from maxapi.enums.chat_type import ChatType
from maxapi.enums.parse_mode import ParseMode
from maxapi.methods.types.sended_message import SendedMessage
from maxapi.types.callback import Callback
from maxapi.types.message import Message, MessageBody, Recipient
from maxapi.types.updates import BotStarted, MessageCallback, MessageCreated
from maxapi.types.users import User

os.environ.setdefault("MAX_BOT_TOKEN", "simulation-token")
os.environ.setdefault("DEMO_STATUS_SIMULATION", "false")

from app.config import load_config  # noqa: E402
from app.main import build_dispatcher  # noqa: E402
from app.services import setup_services  # noqa: E402

CHAT_ID = 1000
USER_ID = 42
USER = User(
    user_id=USER_ID,
    first_name="Степан",
    is_bot=False,
    last_activity_time=0,
)


class FakeBot:
    """Мини-заглушка Bot: хранит «чат» в памяти."""

    def __init__(self) -> None:
        self.parse_mode = ParseMode.HTML
        self.me = User(
            user_id=1,
            first_name="ЖКХ-бот",
            username="smart_city_bot",
            is_bot=True,
            last_activity_time=0,
        )
        self.messages: dict[str, Message] = {}
        self.callback_targets: dict[str, str] = {}
        self.notifications: list[str] = []
        self.sent_count = 0
        self._seq = 0

    def resolve_format(self, format=None, parse_mode=None):  # noqa: A002
        return format if format is not None else self.parse_mode

    async def send_message(
        self,
        chat_id: int | None = None,
        user_id: int | None = None,
        text: str | None = None,
        attachments: list[Any] | None = None,
        **_: Any,
    ) -> SendedMessage:
        self._seq += 1
        self.sent_count += 1
        mid = f"mid-{self._seq}"
        message = self._build_message(mid, text, attachments)
        self.messages[mid] = message
        return SendedMessage(message=message)

    async def edit_message(
        self,
        message_id: str,
        text: str | None = None,
        attachments: list[Any] | None = None,
        **_: Any,
    ) -> None:
        if message_id not in self.messages:
            raise ValueError(f"Сообщение {message_id} не найдено")
        self.messages[message_id] = self._build_message(
            message_id, text, attachments
        )

    async def send_callback(
        self,
        callback_id: str,
        message: Any = None,
        notification: str | None = None,
    ) -> None:
        if notification:
            self.notifications.append(notification)
        if message is None:
            return
        target = self.callback_targets[callback_id]
        await self.edit_message(
            target, text=message.text, attachments=message.attachments
        )

    def _build_message(
        self, mid: str, text: str | None, attachments: list[Any] | None
    ) -> Message:
        self._seq += 1
        return Message(
            recipient=Recipient(
                chat_id=CHAT_ID, user_id=USER_ID, chat_type=ChatType.DIALOG
            ),
            timestamp=0,
            body=MessageBody(
                mid=mid,
                seq=self._seq,
                text=text,
                attachments=attachments or [],
            ),
        )


class Simulation:
    """Помощник: отправляет события в диспетчер и читает текущий экран."""

    def __init__(self) -> None:
        self.bot = FakeBot()
        self.dispatcher = build_dispatcher()
        self._callbacks = 0

    async def start(self) -> None:
        event = BotStarted(
            timestamp=0, chat_id=CHAT_ID, user=USER, user_locale="ru"
        )
        await self._dispatch(event)

    async def send_text(self, text: str) -> None:
        message = Message(
            sender=USER,
            recipient=Recipient(
                chat_id=CHAT_ID, user_id=USER_ID, chat_type=ChatType.DIALOG
            ),
            timestamp=0,
            body=MessageBody(mid="user-msg", seq=0, text=text),
        )
        await self._dispatch(MessageCreated(timestamp=0, message=message))

    async def click(self, payload: str) -> None:
        screen_id = self.screen_id
        if screen_id is None:
            raise AssertionError("Нет активного экрана для нажатия кнопки")

        self._callbacks += 1
        callback_id = f"cb-{self._callbacks}"
        self.bot.callback_targets[callback_id] = screen_id

        event = MessageCallback(
            timestamp=0,
            message=self.bot.messages[screen_id],
            callback=Callback(
                timestamp=0,
                callback_id=callback_id,
                payload=payload,
                user=USER,
            ),
        )
        await self._dispatch(event)

    @property
    def screen_id(self) -> str | None:
        if not self.bot.messages:
            return None
        return list(self.bot.messages)[-1]

    @property
    def screen_text(self) -> str:
        screen_id = self.screen_id
        if screen_id is None:
            return ""
        body = self.bot.messages[screen_id].body
        return body.text or "" if body else ""

    @property
    def buttons(self) -> list[str]:
        screen_id = self.screen_id
        if screen_id is None:
            return []
        body = self.bot.messages[screen_id].body
        if body is None or not body.attachments:
            return []
        keyboard = body.attachments[0]
        return [
            str(button.payload)
            for row in keyboard.payload.buttons
            for button in row
        ]

    async def _dispatch(self, event: Any) -> None:
        event.bot = self.bot
        await self.dispatcher.handle(event)


def check(condition: bool, title: str) -> None:
    """Мини-ассерт с читаемым выводом."""

    status = "✅" if condition else "❌"
    print(f"{status} {title}")
    if not condition:
        raise AssertionError(title)


async def scenario_quick_button(sim: Simulation) -> None:
    """Основной путь: быстрый сценарий → обращение → «Мои обращения»."""

    print("\n=== Сценарий 1: быстрый сценарий ===")

    await sim.start()
    screen_id = sim.screen_id
    check("Здравствуйте" in sim.screen_text, "приветствие показано")
    check(sim.buttons == ["new", "my"], "меню из двух кнопок")

    await sim.click("new")
    check("Новое обращение" in sim.screen_text, "экран быстрых сценариев")
    check("cat:water" in sim.buttons, "есть быстрый сценарий «Вода»")

    await sim.click("cat:water")
    check("Где именно течёт" in sim.screen_text, "задан уточняющий вопрос")

    await sim.send_text("Течёт труба в подъезде на 5 этаже, вода на полу")
    check("Черновик обращения" in sim.screen_text, "сформирован черновик")
    check("draft_done" in sim.buttons, "есть кнопка «Готово»")

    await sim.send_text("Добавь, что вода стекает на 4 этаж")
    check(
        "стекает на 4 этаж" in sim.screen_text,
        "правка текстом попала в черновик",
    )

    await sim.click("draft_done")
    check("Обращение отправлено" in sim.screen_text, "обращение отправлено")
    check("ОБР-" in sim.screen_text, "присвоен номер обращения")
    check("Демо-режим" in sim.screen_text, "модельная интеграция помечена")

    await sim.click("my")
    check("Мои обращения" in sim.screen_text, "открыт список обращений")
    check(
        any(b.startswith("item:") for b in sim.buttons),
        "обращение есть в списке кнопкой",
    )

    item_payload = next(b for b in sim.buttons if b.startswith("item:"))
    await sim.click(item_payload)
    check("Текст обращения" in sim.screen_text, "открыта карточка обращения")
    check("История статусов" in sim.screen_text, "видна история статусов")

    await sim.click("menu")
    check("Здравствуйте" in sim.screen_text, "возврат в главное меню")

    check(
        sim.screen_id == screen_id,
        "вся навигация прошла в ОДНОМ сообщении (edit in place)",
    )
    check(sim.bot.sent_count == 1, "новых сообщений в чат не отправлялось")


async def scenario_free_text(sim: Simulation) -> None:
    """Chat-first путь: житель сразу пишет проблему своими словами."""

    print("\n=== Сценарий 2: свободный текст ===")

    screen_id = sim.screen_id
    await sim.send_text("В подъезде не закрывается дверь и глючит домофон")
    check("Уточняю детали" in sim.screen_text, "AI задал уточнение")

    await sim.send_text("Подъезд 2, началось вчера вечером")
    check("Черновик обращения" in sim.screen_text, "сформирован черновик")
    check("Дверь / домофон" in sim.screen_text, "категория определена сама")

    await sim.click("draft_done")
    check("Обращение отправлено" in sim.screen_text, "второе обращение ушло")

    await sim.click("my")
    check(
        sum(b.startswith("item:") for b in sim.buttons) == 2,
        "в списке два обращения",
    )
    check(sim.screen_id == screen_id, "экран по-прежнему один")


async def scenario_uk_failure(sim: Simulation) -> None:
    """Сбой внешней системы не должен приводить в тупик."""

    print("\n=== Сценарий 3: ошибка отправки в УК ===")

    from app.integrations.uk_client import SubmitResult
    from app.services import get_services

    services = get_services()
    original = services.uk.submit

    async def failing_submit(_request):
        return SubmitResult(ok=False, is_mock=True, error="УК недоступна")

    await sim.click("new")
    await sim.click("cat:light")
    await sim.send_text("Нет света на лестничной клетке, подъезд 1")
    check("Черновик обращения" in sim.screen_text, "черновик готов")

    services.uk.submit = failing_submit  # type: ignore[method-assign]
    await sim.click("draft_done")
    check("Не удалось отправить" in sim.screen_text, "ошибка показана")
    check("draft_done" in sim.buttons, "есть повтор отправки")

    services.uk.submit = original  # type: ignore[method-assign]
    await sim.click("draft_done")
    check("Обращение отправлено" in sim.screen_text, "повтор сработал")

    await sim.click("my")
    check(
        sum(b.startswith("item:") for b in sim.buttons) == 3,
        "дубликат обращения не создан",
    )


async def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    setup_services(load_config())

    sim = Simulation()
    await scenario_quick_button(sim)
    await scenario_free_text(sim)
    await scenario_uk_failure(sim)

    print("\n🎉 Все сценарии пройдены")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError as exc:
        print(f"\n💥 Проверка не прошла: {exc}")
        sys.exit(1)
