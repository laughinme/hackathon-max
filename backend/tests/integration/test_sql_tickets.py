"""Ticket persistence on a real PostgreSQL, schema created by Alembic.

Run: TEST_DATABASE_URL=postgresql+asyncpg://... uv run pytest -m integration
The database is wiped (downgrade base -> upgrade head) on every run.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig

from application.tickets.change_status import ChangeStatusCommand, ChangeTicketStatus
from application.tickets.create_ticket import CreateTicket, CreateTicketCommand
from application.tickets.queries import ListReporterTickets
from domain.tickets.enums import ActorRole, TicketStatus
from domain.tickets.sla import SlaPolicy
from infrastructure.db.engine import make_engine, make_session_factory
from infrastructure.db.uow import SqlUnitOfWork
from tests.fakes import FixedClock

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not set"),
]
BACKEND_DIR = Path(__file__).resolve().parents[2]


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


async def test_ticket_round_trip_with_timeline(session_factory):
    clock = FixedClock()
    uow = lambda: SqlUnitOfWork(session_factory)  # noqa: E731
    created = await CreateTicket(uow, SlaPolicy(), clock).execute(
        CreateTicketCommand(
            reporter_id=42,
            chat_id=-100500,
            category_code="water",
            is_emergency=True,
            description="Топит подвал",
        )
    )
    clock.advance(timedelta(minutes=20))
    await ChangeTicketStatus(uow, clock).execute(
        ChangeStatusCommand(
            ticket_id=created.id,
            target=TicketStatus.IN_PROGRESS,
            actor_role=ActorRole.DISPATCHER,
            actor_id=7,
            comment="аварийка выехала",
        )
    )

    [loaded] = await ListReporterTickets(uow, clock).execute(42)
    assert loaded.number == "2026-00001"
    assert loaded.status is TicketStatus.IN_PROGRESS
    assert loaded.is_emergency and loaded.react_by == created.react_by
    assert [event.status for event in loaded.events] == [
        TicketStatus.REGISTERED,
        TicketStatus.IN_PROGRESS,
    ]
    assert loaded.events[-1].comment == "аварийка выехала"


async def test_sequence_survives_transactions(session_factory):
    clock = FixedClock()
    uow = lambda: SqlUnitOfWork(session_factory)  # noqa: E731
    create = CreateTicket(uow, SlaPolicy(), clock)
    command_ = CreateTicketCommand(42, None, "lift", False, "Лифт")
    numbers = [(await create.execute(command_)).number for _ in range(3)]
    assert numbers == ["2026-00001", "2026-00002", "2026-00003"]
