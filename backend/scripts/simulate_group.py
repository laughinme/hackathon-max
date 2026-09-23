"""Scenario 8 of the simulator: the house chat, through the real dispatcher.

Kept apart from simulate_flow.py to keep files short; it reuses its FakeBot
(negative chat ids become group chats) and the Simulation's dispatcher, so
the router scopes (dialog vs group) are exercised for real.
"""

from __future__ import annotations

from collections.abc import Callable
from itertools import count
from typing import Any

from maxapi.enums.chat_type import ChatType
from maxapi.types.callback import Callback
from maxapi.types.message import Message, MessageBody, Recipient
from maxapi.types.updates.bot_added import BotAdded
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.types.users import User

GROUP = -900_001
_ids = count(1)


def _user(user_id: int, name: str) -> User:
    return User(user_id=user_id, first_name=name, is_bot=False, last_activity_time=0)


ANNA, BORIS, VERA = _user(501, "Анна"), _user(502, "Борис"), _user(503, "Вера")


class HouseChat:
    def __init__(self, sim: Any) -> None:
        self.sim = sim
        self.bot = sim.bot

    async def bot_added(self, by: User) -> None:
        await self.sim._dispatch(  # noqa: SLF001
            BotAdded(timestamp=0, chat_id=GROUP, user=by, is_channel=False)
        )

    async def say(self, user: User, text: str) -> str:
        mid = f"group-msg-{next(_ids)}"
        message = Message(
            sender=user,
            recipient=Recipient(chat_id=GROUP, chat_type=ChatType.CHAT),
            timestamp=0,
            body=MessageBody(mid=mid, seq=0, text=text),
        )
        await self.sim._dispatch(MessageCreated(timestamp=0, message=message))  # noqa: SLF001
        return mid

    async def press(self, user: User, mid: str, payload: str) -> None:
        callback_id = f"group-cb-{next(_ids)}"
        self.bot.callback_targets[callback_id] = mid
        event = MessageCallback(
            timestamp=0,
            message=self.bot.messages[mid],
            callback=Callback(
                timestamp=0, callback_id=callback_id, payload=payload, user=user
            ),
        )
        await self.sim._dispatch(event)  # noqa: SLF001

    def bot_messages(self) -> list[tuple[str, Message]]:
        return [
            (mid, message)
            for mid, message in self.bot.messages.items()
            if message.recipient.chat_id == GROUP
        ]

    def last(self) -> tuple[str, str, list[str]]:
        mid, message = self.bot_messages()[-1]
        return mid, self.text(mid), self.buttons(mid)

    def text(self, mid: str) -> str:
        body = self.bot.messages[mid].body
        return (body.text or "") if body else ""

    def buttons(self, mid: str) -> list[str]:
        body = self.bot.messages[mid].body
        if body is None or not body.attachments:
            return []
        keyboard: Any = body.attachments[0]
        return [
            str(getattr(button, "payload", None) or getattr(button, "url", ""))
            for row in keyboard.payload.buttons
            for button in row
        ]


async def scenario_house_chat(sim: Any, check: Callable[[bool, str], None]) -> None:
    print("\n=== Сценарий 8: домовой чат → заявка → «Я тоже» → карточка ===")
    chat = HouseChat(sim)
    dialog_screens = _dialog_messages(sim)

    await chat.bot_added(ANNA)
    mid, text, buttons = chat.last()
    check("Выберите дом" in text, "бот поздоровался и попросил выбрать дом")
    await chat.press(ANNA, mid, "gbld:psk002")
    check("Чат привязан к дому" in chat.text(mid), "чат привязан к дому")

    await chat.say(VERA, "Всем привет, кто потерял ключи?")
    check(chat.last()[0] == mid, "на обычное сообщение бот молчит")

    await chat.say(BORIS, "Лифт опять не работает во втором подъезде, застревает")
    hint_mid, text, buttons = chat.last()
    check("Похоже на проблему" in text and "Лифт" in text, "бот заметил жалобу")
    file_button = next(b for b in buttons if b.startswith("gfile:"))

    await chat.press(ANNA, hint_mid, file_button)
    card = chat.text(hint_mid)
    check("Заявка №" in card and "Срок устранения" in card, "в чате карточка со сроком")
    check("Поддержали соседи: 1" in card, "автор сообщения учтён как «Я тоже»")
    support = next(b for b in chat.buttons(hint_mid) if b.startswith("gsup:"))
    check(
        any("?start=t_" in b for b in chat.buttons(hint_mid)),
        "есть ссылка «Следить в личке»",
    )

    await chat.press(VERA, hint_mid, support)
    check("Поддержали соседи: 2" in chat.text(hint_mid), "«Я тоже» увеличил счётчик")
    await chat.press(VERA, hint_mid, support)
    check(
        "Вы уже поддержали" in sim.bot.notifications[-1],
        "повторный голос не считается",
    )

    await chat.say(VERA, "У нас лифт снова сломан, второй подъезд, стоит")
    check(chat.last()[0] == hint_mid, "поддержавшему повторно не отвечаем")
    await chat.say(_user(504, "Глеб"), "Лифт не работает, второй подъезд уже день")
    known_mid, text, _ = chat.last()
    check("уже сообщили" in text, "похожая жалоба → предложение «Я тоже», не дубль")

    check(
        _dialog_messages(sim) == dialog_screens,
        "личные сценарии на сообщения группы не реагировали",
    )
    [ticket] = [t for t in await sim.services.list_tickets.execute(ANNA.user_id)]
    from application.tickets.change_status import ChangeStatusCommand
    from domain.tickets.enums import ActorRole, TicketStatus

    await sim.services.become_demo_dispatcher.execute(900)
    await sim.services.change_status.execute(
        ChangeStatusCommand(
            ticket.id, TicketStatus.IN_PROGRESS, ActorRole.DISPATCHER, 900
        )
    )
    while await sim.deliver.execute():
        pass
    check("В работе" in chat.text(hint_mid), "карточка в чате обновилась по статусу")


def _dialog_messages(sim: Any) -> int:
    return len([m for m in sim.bot.messages.values() if m.recipient.chat_id > 0])
