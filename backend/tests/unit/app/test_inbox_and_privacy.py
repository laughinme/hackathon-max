from typing import Any, cast

import pytest

from api.webhooks import max as webhook
from api.webhooks.max import WebhookReceiver, dedup_key
from application.tickets.create_ticket import CreateTicketCommand
from domain.tickets.entities import ANONYMOUS_REPORTER
from infrastructure.memory.tickets import InMemoryInbox
from tests.fakes import FixedClock, make_world

MESSAGE = {
    "update_type": "message_created",
    "timestamp": 1,
    "message": {"body": {"mid": "mid.1", "text": "лифт"}},
}
CALLBACK = {
    "update_type": "message_callback",
    "timestamp": 2,
    "callback": {"callback_id": "cb.1", "payload": "menu"},
}


def test_dedup_key_uses_message_and_callback_ids():
    assert dedup_key(MESSAGE) == "message_created:mid.1"
    assert dedup_key(CALLBACK) == "cb:cb.1"
    started = {"update_type": "bot_started", "timestamp": 5, "user": {"user_id": 7}}
    assert dedup_key(started) == "bot_started:5:None:7"


async def test_redelivered_update_reaches_handlers_once(monkeypatch):
    handled: list[object] = []

    class CountingDispatcher:
        async def handle(self, event: object) -> None:
            handled.append(event)

    async def fake_parse(event_json: dict[str, Any], bot: object) -> object:
        return event_json

    monkeypatch.setattr(webhook, "process_update_webhook", fake_parse)
    receiver = WebhookReceiver(
        cast(Any, CountingDispatcher()),
        bot=cast(Any, None),
        secret="s",
        inbox=InMemoryInbox(),
        clock=FixedClock(),
    )
    for payload in (MESSAGE, MESSAGE, CALLBACK, MESSAGE):
        await receiver._process(payload)  # noqa: SLF001

    assert handled == [MESSAGE, CALLBACK]


@pytest.mark.parametrize("was_dispatcher", [False, True])
async def test_forget_user_unbinds_and_detaches_tickets(was_dispatcher):
    world = make_world()
    await world.services.bind_resident.execute(42, "psk001")
    if was_dispatcher:
        world.add_dispatcher(42)
    ticket = await world.services.create_ticket.execute(
        CreateTicketCommand(42, 42, "lift", False, "Лифт стоит")
    )

    assert await world.services.forget_user.execute(42) == 1

    identity = await world.services.identify.execute(42)
    assert identity.residency is None and identity.dispatcher is None
    assert world.store.tickets[ticket.id].reporter_id == ANONYMOUS_REPORTER
    assert await world.services.list_tickets.execute(42) == []
