"""The CRM loop on a real PostgreSQL: event feed order, webhook cursor, links.

Run: TEST_DATABASE_URL=postgresql+asyncpg://... uv run pytest -m integration
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.services import build_services
from application.integrations.apply_external_status import ExternalStatusCommand
from application.integrations.configure_webhook import WebhookCommand
from application.tickets.create_ticket import CreateTicketCommand
from domain.tickets.enums import TicketStatus
from infrastructure.db.integration_feed import SqlIntegrationFeed
from infrastructure.db.ticket_queries import SqlTicketQueries
from infrastructure.db.uow import SqlUnitOfWork
from infrastructure.seed.demo_data import build_demo_dataset
from infrastructure.seed.loaders import load_into_postgres
from tests.fakes import (
    CONFIG,
    FixedClock,
    RecordingWebhookSender,
    StaticClassifier,
    classification,
)
from tests.integration.test_sql_tickets import DATABASE_URL, session_factory

__all__ = ["session_factory"]  # the fixture, shared with the tickets tests

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is not set"),
]
RESIDENT, DISPATCHER = 42, 7


async def test_crm_loop_on_postgres(session_factory):
    clock = FixedClock()
    await load_into_postgres(
        session_factory, build_demo_dataset(clock.now(), tickets_count=3)
    )
    webhooks = RecordingWebhookSender()
    services = build_services(
        CONFIG,
        uow_factory=lambda: SqlUnitOfWork(session_factory),
        queries=SqlTicketQueries(session_factory),
        integration_feed=SqlIntegrationFeed(session_factory, commit_lag=timedelta(0)),
        clock=clock,
        classifier=StaticClassifier(classification()),
        webhook_sender=webhooks,
    )
    integrations = services.integrations
    await services.bind_resident.execute(RESIDENT, "psk001")
    await services.become_demo_dispatcher.execute(DISPATCHER)

    connected = await integrations.connect.execute(DISPATCHER, "CRM")
    await integrations.configure_webhook.execute(
        WebhookCommand(connected.integration.id, "https://crm.example.ru/hook")
    )
    await integrations.set_status_map.execute(
        connected.integration.id, {"WORKING": "in_progress"}
    )
    integration = await integrations.authenticate.execute(connected.api_key)
    assert integration.status_map == {"WORKING": TicketStatus.IN_PROGRESS}

    webhooks.answer = {"external_id": "58391", "external_number": "АДС-58391"}
    first = await services.create_ticket.execute(
        CreateTicketCommand(RESIDENT, None, "lift", False, "Лифт не работает")
    )
    clock.advance(timedelta(seconds=1))
    second = await services.create_ticket.execute(
        CreateTicketCommand(RESIDENT, None, "water", False, "Течёт кран")
    )

    assert await integrations.deliver_webhooks.execute() == 2
    assert [e["ticket"]["number"] for _, e in webhooks.sent] == [
        first.number,
        second.number,
    ]
    assert await integrations.deliver_webhooks.execute() == 0

    # The first answer linked 58391; the second tried the same record for
    # another ticket and was ignored instead of stealing the link.
    result = await integrations.apply_status.execute(
        ExternalStatusCommand(integration, "ext:58391", "WORKING", "Мастер выехал")
    )
    assert result.applied and result.ticket.view.id == first.id
    assert result.ticket.link is not None
    assert result.ticket.link.external_status == "WORKING"
    again = await integrations.apply_status.execute(
        ExternalStatusCommand(integration, "ext:58391", "WORKING")
    )
    assert not again.applied

    integration = await integrations.authenticate.execute(connected.api_key)
    me = await integrations.describe.execute(integration)
    assert me.pending_events == 1  # the CRM's own change, skipped on delivery
    assert await integrations.deliver_webhooks.execute() == 1
    assert len(webhooks.sent) == 2  # no echo
    me = await integrations.describe.execute(
        await integrations.authenticate.execute(connected.api_key)
    )
    assert me.pending_events == 0 and me.last_error is None

    page = await integrations.list_events.execute(integration, 0, 10)
    assert [e["type"] for e in page.events] == ["ticket.created", "ticket.created"]
    tickets = await integrations.list_tickets.execute(integration, None, 1)
    assert tickets.next_cursor is not None
    rest = await integrations.list_tickets.execute(integration, tickets.next_cursor, 50)
    numbers = {t.view.number for t in (*tickets.tickets, *rest.tickets)}
    assert {first.number, second.number} <= numbers
