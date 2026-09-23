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
from maxapi.types.updates.bot_started import BotStarted
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.types.users import User

os.environ.setdefault("MAX_TOKEN", "simulation-token")
# Not used: the simulator stores tickets in memory.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://simulation/unused")

from app.config import load_config  # noqa: E402
from app.main import build_dispatcher  # noqa: E402
from app.services import Services, build_services  # noqa: E402
from application.notifications.deliver import DeliverNotifications  # noqa: E402
from bot.notifications import MaxNotificationSender  # noqa: E402
from infrastructure.clock import SystemClock  # noqa: E402
from infrastructure.memory.tickets import (  # noqa: E402
    InMemoryOutboxReader,
    InMemoryStore,
    InMemoryTicketQueries,
    InMemoryUnitOfWork,
)
from infrastructure.ml.rule_based import RuleBasedClassifier  # noqa: E402
from infrastructure.seed.demo_data import build_demo_dataset  # noqa: E402
from infrastructure.seed.loaders import load_into_memory  # noqa: E402

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
        self.messages[message_id] = self._build_message(message_id, text, attachments)

    async def delete_message(self, message_id: str) -> None:
        if self.messages.pop(message_id, None) is None:
            raise ValueError(f"Сообщение {message_id} не найдено")

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

    def __init__(self, services: Services) -> None:
        self.services = services
        self.bot = FakeBot()
        self.dispatcher = build_dispatcher(services)
        self._callbacks = 0
        self.deliver: Any = None

    async def start(self) -> None:
        event = BotStarted(timestamp=0, chat_id=CHAT_ID, user=USER, user_locale="ru")
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
        keyboard: Any = body.attachments[0]  # always our inline keyboard
        return [
            str(button.payload) for row in keyboard.payload.buttons for button in row
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
    """Main path: building -> quick category -> ticket with legal deadline."""

    print("\n=== Сценарий 1: выбор дома и быстрый сценарий ===")

    await sim.start()
    screen_id = sim.screen_id
    check("Здравствуйте" in sim.screen_text, "приветствие показано")
    check("demo_disp" in sim.buttons, "есть вход диспетчера для демо")

    await sim.click("new")
    check("Выберите ваш дом" in sim.screen_text, "сначала просим выбрать дом")
    await sim.click("bld:psk001")
    check("Ваш дом" in sim.screen_text, "дом сохранён, показано меню")

    await sim.click("new")
    check("Новая заявка" in sim.screen_text, "экран быстрых сценариев")
    await sim.click("cat:water")
    check("Где именно течёт" in sim.screen_text, "задан уточняющий вопрос")

    await sim.send_text("Течёт труба в подъезде на 5 этаже, вода на полу")
    check("Это авария?" in sim.screen_text, "классификатор не уверен: спросили")
    await sim.click("emg:no")
    check("Черновик заявки" in sim.screen_text, "сформирован черновик")
    check("Правила № 170" in sim.screen_text, "показано основание срока")

    await sim.send_text("Добавь, что вода стекает на 4 этаж")
    check("стекает на 4 этаж" in sim.screen_text, "правка попала в черновик")

    await sim.click("draft_done")
    check("Заявка зарегистрирована" in sim.screen_text, "заявка зарегистрирована")
    check("№ 2026-00121" in sim.screen_text, "номер продолжает демо-историю")
    check("Тестовый режим" in sim.screen_text, "демо-данные помечены")

    await sim.click("my")
    item_payload = next(b for b in sim.buttons if b.startswith("item:"))
    await sim.click(item_payload)
    check("История" in sim.screen_text, "карточка с историей")

    await sim.click("menu")
    check(sim.screen_id != screen_id, "после текста экран переехал вниз")
    check(len(sim.bot.messages) == 1, "в чате всегда один экран бота")
    check(sim.bot.sent_count == 3, "новый экран только на сообщения, не на кнопки")


async def scenario_free_text(sim: Simulation) -> None:
    """Chat-first: the resident writes the problem in their own words."""

    print("\n=== Сценарий 2: свободный текст, авария ===")

    await sim.send_text("В подвале прорвало трубу, топит всё")
    check("Уточняю детали" in sim.screen_text, "AI задал уточнение")
    await sim.send_text("Подъезд 2, началось час назад")
    check("Это авария?" in sim.screen_text, "спросили про аварию")
    await sim.click("emg:yes")
    check("ПП РФ № 416, п. 13" in sim.screen_text, "аварийный норматив")
    check("Реакция аварийной службы" in sim.screen_text, "срок реакции 30 минут")
    await sim.click("draft_done")
    check("Заявка зарегистрирована" in sim.screen_text, "вторая заявка")


async def scenario_storage_failure(sim: Simulation) -> None:
    """A storage failure keeps the draft and never creates a duplicate."""

    print("\n=== Сценарий 3: сбой хранилища при отправке ===")

    create = sim.services.create_ticket
    original = create.execute

    async def failing_execute(_command):
        raise ConnectionError("database is down")

    await sim.click("new")
    await sim.click("cat:light")
    await sim.send_text("Не горит лампа на лестничной клетке, подъезд 1")
    await sim.click("emg:no")

    object.__setattr__(create, "execute", failing_execute)
    await sim.click("draft_done")
    check("Не удалось зарегистрировать" in sim.screen_text, "ошибка показана")
    object.__setattr__(create, "execute", original)
    await sim.click("draft_done")
    check("Заявка зарегистрирована" in sim.screen_text, "повтор сработал")

    await sim.click("my")
    check(sum(b.startswith("item:") for b in sim.buttons) == 3, "дубликата нет")


async def scenario_dispatcher_and_resident(sim: Simulation) -> None:
    """Dispatcher works the queue in the chat; the resident confirms the fix."""

    print("\n=== Сценарий 5: диспетчер → уведомление → подтверждение ===")

    await sim.click("menu")
    await sim.click("demo_disp")
    check("Вы диспетчер" in sim.screen_text, "включена роль диспетчера (демо)")
    await sim.click("dq")
    check("Очередь заявок" in sim.screen_text, "открыта очередь")
    check("просрочено" in sim.screen_text, "видно число просрочек")

    [mine, *_] = await sim.services.list_tickets.execute(USER_ID)
    await sim.click(f"dt:{mine.id}")
    check(f"№ {mine.number}" in sim.screen_text, "карточка заявки жителя")
    await sim.click(f"ds:{mine.id}:in_progress")
    check("Напишите комментарий" in sim.screen_text, "спросили комментарий")
    await sim.send_text("электрик придёт завтра к 10:00")
    check("В работе" in sim.screen_text, "статус изменён")

    await sim.click(f"ds:{mine.id}:done")
    await sim.click("dsc")
    check("Выполнена" in sim.screen_text, "отмечено выполнение")

    sent_before = sim.bot.sent_count
    delivered = await sim.deliver.execute()
    check(delivered == 2, "два уведомления жителю доставлены")
    check(sim.bot.sent_count == sent_before + 2, "уведомления пришли сообщениями")
    check("Проблема устранена?" in sim.screen_text, "последнее — вопрос о выполнении")
    check(f"ok:{mine.id}" in sim.buttons, "есть кнопка «Да, всё работает»")

    await sim.click(f"ok:{mine.id}")
    check("Закрыта" in sim.screen_text, "житель подтвердил, заявка закрыта")
    check(
        await sim.deliver.execute() == 0, "жителю не шлём уведомление о его же действии"
    )


async def scenario_llm_service(sim: Simulation) -> None:
    """Бот работает поверх ответов модели, а не заглушки.

    Модель подменяется скриптованным клиентом: проверяем, что бот
    корректно показывает вопрос и черновик из JSON-решения модели
    и что при недоступности модели сценарий не встаёт.
    """

    print("\n=== Сценарий 4: AI-слой на модели ===")

    from infrastructure.llm.client import LLMUnavailableError
    from infrastructure.llm.schemas import ModelDecision, Slots
    from infrastructure.llm.service import LLMAIService

    ask = ModelDecision(
        action="ask",
        category="cleaning",
        urgency="обычная",
        slots=Slots(problem="не вывозят мусор"),
        missing_slots=["location", "started_at"],
        question="Где именно стоит мусор и как давно?",
        explanation="Отвечает УК (санитарное содержание).",
    )
    draft = ModelDecision(
        action="draft",
        category="cleaning",
        urgency="обычная",
        slots=Slots(
            problem="не вывозят мусор",
            location="контейнерная площадка у дома",
            started_at="неделю",
        ),
        missing_slots=[],
        draft="Прошу организовать вывоз мусора с контейнерной площадки.",
        explanation="Отвечает УК (санитарное содержание).",
    )

    class ScriptedClient:
        """Клиент модели со сценарным ответом."""

        def __init__(self, replies: list[object]) -> None:
            self._replies = list(replies)

        async def complete(self, messages: list[Any]) -> str:
            reply = self._replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return str(reply)

    services = sim.services
    original_ai = services.ai
    replies: list[object] = [
        ask.as_training_target(),
        "не json, модель сорвалась",
        draft.as_training_target(),
        LLMUnavailableError("сервис модели недоступен"),
        LLMUnavailableError("сервис модели недоступен"),
    ]
    object.__setattr__(
        services,
        "ai",
        LLMAIService(ScriptedClient(replies)),  # type: ignore[arg-type]
    )

    try:
        await sim.click("menu")
        await sim.send_text("У нас не вывозят мусор от контейнеров")
        check(
            "Где именно стоит мусор" in sim.screen_text,
            "показан вопрос, сформулированный моделью",
        )

        await sim.send_text("Контейнерная площадка у дома, уже неделю")
        await sim.click("emg:no")
        check(
            "Прошу организовать вывоз мусора" in sim.screen_text,
            "показан черновик от модели (после починки невалидного JSON)",
        )

        await sim.send_text("добавь, что появился запах")
        check(
            "Уточнение от заявителя" in sim.screen_text,
            "при недоступности модели сработал откат на заглушку",
        )
    finally:
        object.__setattr__(services, "ai", original_ai)


async def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    clock = SystemClock()
    store = InMemoryStore()
    load_into_memory(store, build_demo_dataset(clock.now()))
    services = build_services(
        load_config(),
        uow_factory=lambda: InMemoryUnitOfWork(store),
        queries=InMemoryTicketQueries(store),
        clock=clock,
        classifier=RuleBasedClassifier(),
    )

    sim = Simulation(services)
    sim.deliver = DeliverNotifications(
        InMemoryOutboxReader(store),
        MaxNotificationSender(sim.bot),  # type: ignore[arg-type]
        clock,
    )
    await scenario_quick_button(sim)
    await scenario_free_text(sim)
    await scenario_storage_failure(sim)
    await scenario_llm_service(sim)
    await scenario_dispatcher_and_resident(sim)

    print("\n🎉 Все сценарии пройдены")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError as exc:
        print(f"\n💥 Проверка не прошла: {exc}")
        sys.exit(1)
