from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest

from application.tickets.create_ticket import CreateTicketCommand
from bot.notifications import MaxNotificationSender, render
from domain.notifications.entities import Notification, NotificationKind
from domain.tickets.exceptions import NotTicketReporterError, TicketNotOverdueError
from tests.fakes import make_world

REPORTER = 42
DISPATCHERS = (7, 8)
LIFT_DEADLINE = timedelta(days=1)


async def _world_with_ticket():
    world = make_world()
    await world.services.bind_resident.execute(REPORTER, "psk001")
    for dispatcher in DISPATCHERS:
        world.add_dispatcher(dispatcher)
    ticket = await world.services.create_ticket.execute(
        CreateTicketCommand(REPORTER, REPORTER, "lift", False, "Лифт стоит")
    )
    return world, ticket


def _outbox(world) -> list[Notification]:
    return [entry.notification for entry in world.store.outbox.values()]


async def test_nothing_happens_before_the_deadline():
    world, _ = await _world_with_ticket()
    world.clock.advance(LIFT_DEADLINE - timedelta(minutes=1))

    assert await world.services.detect_overdue.execute() == 0
    assert _outbox(world) == []


async def test_overdue_is_reported_once_to_reporter_and_every_dispatcher():
    world, ticket = await _world_with_ticket()
    world.clock.advance(LIFT_DEADLINE + timedelta(minutes=1))

    assert await world.services.detect_overdue.execute() == 1
    assert await world.services.detect_overdue.execute() == 0

    sent = {(n.recipient_user_id, n.kind) for n in _outbox(world)}
    assert sent == {
        (REPORTER, NotificationKind.TICKET_OVERDUE),
        (7, NotificationKind.TICKET_OVERDUE_DISPATCHER),
        (8, NotificationKind.TICKET_OVERDUE_DISPATCHER),
    }
    assert world.store.tickets[ticket.id].overdue_notified_at == world.clock.now()


async def test_escalation_is_refused_before_the_deadline():
    world, ticket = await _world_with_ticket()

    with pytest.raises(TicketNotOverdueError):
        await world.services.escalate.execute(ticket.id, REPORTER)
    assert _outbox(world) == []


async def test_only_the_reporter_can_escalate():
    world, ticket = await _world_with_ticket()
    world.clock.advance(LIFT_DEADLINE * 2)

    with pytest.raises(NotTicketReporterError):
        await world.services.escalate.execute(ticket.id, 99)


async def test_escalation_queues_the_document_and_keeps_the_first_date():
    world, ticket = await _world_with_ticket()
    world.clock.advance(LIFT_DEADLINE * 2)
    first = await world.services.escalate.execute(ticket.id, REPORTER)
    world.clock.advance(timedelta(hours=3))
    again = await world.services.escalate.execute(ticket.id, REPORTER)

    assert first.escalated_at == again.escalated_at
    kinds = [n.kind for n in _outbox(world)]
    assert kinds == [NotificationKind.ESCALATION_DOCUMENT] * 2


async def test_view_says_when_escalation_is_possible():
    world, ticket = await _world_with_ticket()
    view = await world.services.get_ticket.execute(ticket.id, REPORTER)
    assert not view.can_escalate

    world.clock.advance(LIFT_DEADLINE * 2)
    view = await world.services.get_ticket.execute(ticket.id, REPORTER)
    assert view.can_escalate


async def test_document_is_a_pdf_named_after_the_ticket():
    world, ticket = await _world_with_ticket()
    world.clock.advance(LIFT_DEADLINE * 2)

    document = await world.services.escalation_document.execute(ticket.id)

    assert document.content.startswith(b"%PDF")
    assert document.filename == f"zhaloba-gzhi-{ticket.number}.pdf"


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send_message(self, **kwargs: Any) -> None:
        self.messages.append(kwargs)


async def test_sender_attaches_the_pdf_for_escalation():
    world, ticket = await _world_with_ticket()
    world.clock.advance(LIFT_DEADLINE * 2)
    await world.services.escalate.execute(ticket.id, REPORTER)
    [notification] = _outbox(world)
    bot = FakeBot()

    await MaxNotificationSender(
        cast(Any, bot), world.services.escalation_document
    ).send(notification)

    [message] = bot.messages
    [attachment] = message["attachments"]
    assert attachment.filename.endswith(".pdf")
    assert attachment.buffer.startswith(b"%PDF")
    assert "жилищную инспекцию" in message["text"]


def test_every_notification_kind_has_a_text():
    for kind in NotificationKind:
        note = SimpleNamespace(
            kind=kind, ticket_number="2026-00001", status="in_progress", comment=None
        )
        assert render(cast(Notification, note))
