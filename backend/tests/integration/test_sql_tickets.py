"""Persistence on a real PostgreSQL; schema created by Alembic, demo data seeded.

Run: TEST_DATABASE_URL=postgresql+asyncpg://... uv run pytest -m integration
The database is wiped (downgrade base -> upgrade head) for every test.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig

from app.services import build_services
from application.notifications.deliver import DeliverNotifications
from application.tickets.change_status import ChangeStatusCommand
from application.tickets.create_ticket import CreateTicketCommand
from domain.tickets.enums import ActorRole, TicketStatus
from infrastructure.db.dialog_context import PostgresDialogContext
from infrastructure.db.engine import make_engine, make_session_factory
from infrastructure.db.outbox import SqlOutboxReader
from infrastructure.db.ticket_queries import SqlTicketQueries
from infrastructure.db.uow import SqlUnitOfWork
from infrastructure.seed.demo_data import build_demo_dataset
from infrastructure.seed.loaders import load_into_postgres
from tests.fakes import (
    CONFIG,
    FixedClock,
    RecordingSender,
    StaticClassifier,
    classification,
)

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not set"),
]
BACKEND_DIR = Path(__file__).resolve().parents[2]
RESIDENT, DISPATCHER = 42, 7


@pytest.fixture
async def session_factory():
    assert DATABASE_URL is not None
    config = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    engine = make_engine(DATABASE_URL)

    def migrate(connection) -> None:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        command.upgrade(config, "head")

    async with engine.begin() as connection:
        await connection.run_sync(migrate)
    yield make_session_factory(engine)
    await engine.dispose()


@pytest.fixture
async def world(session_factory):
    clock = FixedClock()
    dataset = build_demo_dataset(clock.now(), tickets_count=10)
    assert await load_into_postgres(session_factory, dataset)
    assert not await load_into_postgres(session_factory, dataset)  # idempotent
    services = build_services(
        CONFIG,
        uow_factory=lambda: SqlUnitOfWork(session_factory),
        queries=SqlTicketQueries(session_factory),
        clock=clock,
        classifier=StaticClassifier(classification()),
    )
    await services.bind_resident.execute(RESIDENT, "psk001")
    await services.become_demo_dispatcher.execute(DISPATCHER)
    return services, clock, session_factory


async def test_ticket_lifecycle_with_queue_and_timeline(world):
    services, clock, _ = world
    created = await services.create_ticket.execute(
        CreateTicketCommand(RESIDENT, RESIDENT, "water", True, "Топит подвал")
    )
    assert created.number == "2026-00011"  # continues after 10 synthetic tickets
    assert created.building_address.startswith("г. Псков")

    clock.advance(timedelta(minutes=20))
    await services.change_status.execute(
        ChangeStatusCommand(
            created.id,
            TicketStatus.IN_PROGRESS,
            ActorRole.DISPATCHER,
            DISPATCHER,
            "выехали",
        )
    )
    [mine] = await services.list_tickets.execute(RESIDENT)
    assert mine.status is TicketStatus.IN_PROGRESS
    assert [e.status for e in mine.events] == [
        TicketStatus.REGISTERED,
        TicketStatus.IN_PROGRESS,
    ]
    queue = await services.list_queue.execute(DISPATCHER)
    assert created.id in {ticket.id for ticket in queue}
    deadlines = [ticket.resolve_by for ticket in queue]
    assert deadlines == sorted(deadlines)


async def test_outbox_delivers_once_and_retries_after_failure(world):
    services, clock, session_factory = world
    created = await services.create_ticket.execute(
        CreateTicketCommand(RESIDENT, RESIDENT, "lift", False, "Лифт")
    )
    await services.change_status.execute(
        ChangeStatusCommand(
            created.id, TicketStatus.DONE, ActorRole.DISPATCHER, DISPATCHER
        )
    )
    sender = RecordingSender(fail_times=1)
    deliver = DeliverNotifications(SqlOutboxReader(session_factory), sender, clock)

    assert await deliver.execute() == 0  # MAX down: retry scheduled
    assert await deliver.execute() == 0  # not due yet
    clock.advance(timedelta(minutes=1))
    assert await deliver.execute() == 1
    clock.advance(timedelta(hours=1))
    assert await deliver.execute() == 0  # never twice
    assert [n.status for n in sender.sent] == ["done"]


async def test_dialog_state_survives_a_new_context_object(world):
    _, _, session_factory = world
    first = PostgresDialogContext(1000, RESIDENT, session_factory=session_factory)
    await first.set_state("CreateRequest:editing_draft")
    await first.update_data(draft="Течёт кран", category="water")

    restarted = PostgresDialogContext(1000, RESIDENT, session_factory=session_factory)
    assert await restarted.get_state() == "CreateRequest:editing_draft"
    assert await restarted.get_data() == {"draft": "Течёт кран", "category": "water"}
    await restarted.clear()
    assert await first.get_state() is None


async def test_overdue_watch_and_escalation_on_postgres(world):
    services, clock, session_factory = world
    ticket = await services.create_ticket.execute(
        CreateTicketCommand(RESIDENT, RESIDENT, "lift", False, "Лифт не работает")
    )
    clock.advance(timedelta(days=2))

    # Ours plus seeded ones that ran out during these two days; tickets already
    # overdue at seed time are not reported again.
    assert await services.detect_overdue.execute() >= 1
    assert await services.detect_overdue.execute() == 0

    view = await services.escalate.execute(ticket.id, RESIDENT)
    assert view.escalated_at == clock.now()
    document = await services.escalation_document.execute(ticket.id)
    assert document.content.startswith(b"%PDF")

    reader = SqlOutboxReader(session_factory)
    pending = await reader.claim_batch(50, clock.now())
    kinds = [
        p.notification.kind for p in pending if p.notification.ticket_id == ticket.id
    ]
    assert sorted(kinds) == [
        "escalation_document",
        "ticket_overdue",
        "ticket_overdue_dispatcher",
    ]


async def test_house_chat_flow_and_inbox_on_postgres(world):
    from application.chats.file_from_chat import FileFromChatCommand
    from application.chats.spot_complaint import NewProblem
    from infrastructure.db.inbox import SqlInbox

    services, clock, session_factory = world
    chat, author, neighbour = -555, 901, 902
    await services.register_chat.execute(chat, author)
    await services.bind_chat.execute(chat, "psk001", author)
    spotted = await services.spot_complaint.execute(
        chat, author, "m.1", "Лифт опять не работает, застрял между этажами"
    )
    assert isinstance(spotted, NewProblem)
    ticket = await services.file_from_chat.execute(
        FileFromChatCommand(spotted.hint.id, RESIDENT, card_mid="card.1")
    )
    again = await services.file_from_chat.execute(
        FileFromChatCommand(spotted.hint.id, neighbour, card_mid="card.1")
    )
    assert again.id == ticket.id
    assert ticket.chat_card_mid == "card.1" and ticket.supporter_ids == (author,)

    result = await services.support_ticket.execute(ticket.id, neighbour)
    assert result.counted and result.ticket.supporter_ids == (author, neighbour)

    inbox = SqlInbox(session_factory)
    assert await inbox.register("cb:1", clock.now())
    assert not await inbox.register("cb:1", clock.now())
    assert await inbox.purge(clock.now() + timedelta(days=4)) == 1
