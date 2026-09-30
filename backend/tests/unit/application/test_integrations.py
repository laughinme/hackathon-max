"""The CRM loop on the in-memory world: MAX ticket -> webhook -> CRM status ->
resident, with retries, ordering, echo suppression and the status map."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest

from application.errors import TicketNotFoundError
from application.integrations.apply_external_status import ExternalStatusCommand
from application.integrations.configure_webhook import WebhookCommand
from application.integrations.dto import ExternalRecord
from application.integrations.link_ticket import LinkTicketCommand
from application.tickets.change_status import ChangeStatusCommand
from application.tickets.create_ticket import CreateTicketCommand
from domain.housing.entities import Building, ManagementCompany
from domain.housing.exceptions import NotADispatcherError
from domain.integrations.entities import Integration, IntegrationEventType
from domain.integrations.exceptions import (
    ExternalIdTakenError,
    InvalidApiKeyError,
    UnknownExternalStatusError,
)
from domain.notifications.entities import NotificationKind
from domain.tickets.enums import ActorRole, TicketStatus
from domain.tickets.exceptions import ActionNotAllowedError
from tests.fakes import World, make_world

REPORTER, DISPATCHER = 42, 7
HOOK = "https://crm.example.ru/hooks/domovoy"


@pytest.fixture
async def world() -> World:
    world = make_world()
    await world.services.bind_resident.execute(REPORTER, "psk001")
    world.add_dispatcher(DISPATCHER)
    return world


async def connect(world: World, *, webhook: bool = True) -> tuple[Integration, str]:
    connected = await world.services.integrations.connect.execute(DISPATCHER, "CRM")
    if webhook:
        await world.services.integrations.configure_webhook.execute(
            WebhookCommand(connected.integration.id, HOOK)
        )
    integration = await world.services.integrations.authenticate.execute(
        connected.api_key
    )
    return integration, connected.api_key


async def new_ticket(world: World, text: str = "Лифт не работает"):
    return await world.services.create_ticket.execute(
        CreateTicketCommand(REPORTER, None, "lift", False, text)
    )


async def deliver(world: World) -> int:
    return await world.services.integrations.deliver_webhooks.execute()


def walk(value: Any) -> tuple[set[str], list[int]]:
    """Every key and every integer inside a JSON value."""

    keys: set[str] = set()
    numbers: list[int] = []
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(key)
            inner_keys, inner_numbers = walk(item)
            keys |= inner_keys
            numbers += inner_numbers
    elif isinstance(value, list):
        for item in value:
            inner_keys, inner_numbers = walk(item)
            keys |= inner_keys
            numbers += inner_numbers
    elif isinstance(value, int) and not isinstance(value, bool):
        numbers.append(value)
    return keys, numbers


def sent_types(world: World) -> list[str]:
    return [envelope["type"] for _, envelope in world.webhooks.sent]


async def fresh(world: World, integration: Integration) -> Integration:
    """The integration as stored now (the relay updates its cursor)."""

    return world.store.integrations[integration.id]


async def test_only_a_dispatcher_connects_and_the_key_works_until_revoked(world):
    with pytest.raises(NotADispatcherError):
        await world.services.integrations.connect.execute(REPORTER, "CRM")

    integration, key = await connect(world)
    assert key.startswith("dmv_") and integration.company_id == world.company.id
    assert key not in repr(world.store.integrations)  # only the hash is kept

    await world.services.integrations.revoke.execute(DISPATCHER, integration.id)
    with pytest.raises(InvalidApiKeyError):
        await world.services.integrations.authenticate.execute(key)
    with pytest.raises(InvalidApiKeyError):
        await world.services.integrations.authenticate.execute("dmv_forged")


async def test_new_ticket_reaches_the_crm_and_its_answer_links_the_numbers(world):
    integration, _ = await connect(world)
    world.webhooks.answer = {"external_id": "58391", "external_number": "АДС-58391"}
    ticket = await new_ticket(world)

    assert await deliver(world) == 1
    url, envelope = world.webhooks.sent[0]
    assert url == HOOK and envelope["type"] == "ticket.created"
    assert envelope["ticket"]["number"] == ticket.number
    assert envelope["ticket"]["deadlines"]["legal_basis"]
    keys, numbers = walk(envelope)
    assert not {"reporter_id", "actor_id", "user_id", "supporter_ids"} & keys
    assert REPORTER not in numbers  # no MAX user ids leave the system

    linked = await world.services.integrations.get_ticket.execute(
        integration, "ext:58391"
    )
    assert linked.view.id == ticket.id and linked.link is not None
    assert linked.link.external_number == "АДС-58391"
    assert await deliver(world) == 0  # nothing is sent twice


async def test_crm_status_reaches_the_resident_and_is_not_echoed_back(world):
    integration, _ = await connect(world)
    ticket = await new_ticket(world)
    await deliver(world)
    world.store.outbox.clear()

    result = await world.services.integrations.apply_status.execute(
        ExternalStatusCommand(
            integration, ticket.number, "in_progress", "Мастер выехал"
        )
    )
    assert result.applied and result.ticket.view.status is TicketStatus.IN_PROGRESS
    [notice] = [e.notification for e in world.store.outbox.values()]
    assert notice.kind is NotificationKind.TICKET_STATUS_CHANGED
    assert notice.recipient_user_id == REPORTER and notice.comment == "Мастер выехал"

    await deliver(world)
    assert sent_types(world) == ["ticket.created"]  # its own change is not echoed
    page = await world.services.integrations.list_events.execute(integration, 0, 50)
    assert [e["type"] for e in page.events] == ["ticket.created"]


async def test_repeated_status_is_a_no_op_and_confirming_is_for_the_resident(world):
    integration, _ = await connect(world)
    ticket = await new_ticket(world)
    command = ExternalStatusCommand(integration, str(ticket.id), "done")
    assert (await world.services.integrations.apply_status.execute(command)).applied
    again = await world.services.integrations.apply_status.execute(command)
    assert not again.applied and len(again.ticket.view.events) == 2

    with pytest.raises(ActionNotAllowedError):
        await world.services.integrations.apply_status.execute(
            ExternalStatusCommand(integration, ticket.number, "confirmed")
        )


async def test_status_map_translates_crm_codes_both_ways(world):
    integration, _ = await connect(world)
    view = await world.services.integrations.set_status_map.execute(
        integration.id, {"WORKING": "in_progress", "CLOSED_BY_MASTER": "done"}
    )
    assert view.status_map == {"WORKING": "in_progress", "CLOSED_BY_MASTER": "done"}
    integration = await world.services.integrations.authenticate.execute(
        (await connect(world))[1]
    )  # a second key of the same company has its own (empty) map
    assert integration.status_map == {}

    [first] = [i for i in world.store.integrations.values() if i.status_map]
    ticket = await new_ticket(world)
    await world.services.integrations.apply_status.execute(
        ExternalStatusCommand(
            first, ticket.number, "WORKING", record=ExternalRecord(id="A-1")
        )
    )
    linked = await world.services.integrations.get_ticket.execute(first, "ext:A-1")
    assert linked.view.status is TicketStatus.IN_PROGRESS
    assert linked.link is not None and linked.link.external_status == "WORKING"
    with pytest.raises(UnknownExternalStatusError):
        await world.services.integrations.apply_status.execute(
            ExternalStatusCommand(first, ticket.number, "ON_HOLD")
        )
    with pytest.raises(UnknownExternalStatusError):
        await world.services.integrations.set_status_map.execute(
            first.id, {"X": "closed_forever"}
        )


async def test_resident_answer_goes_to_the_crm_in_order(world):
    integration, _ = await connect(world)
    ticket = await new_ticket(world)
    await world.services.integrations.apply_status.execute(
        ExternalStatusCommand(integration, ticket.number, "done")
    )
    await world.services.change_status.execute(
        ChangeStatusCommand(
            ticket.id, TicketStatus.IN_PROGRESS, ActorRole.RESIDENT, REPORTER, "Течёт"
        )
    )
    await deliver(world)
    assert sent_types(world) == ["ticket.created", "ticket.status_changed"]
    data = world.webhooks.sent[1][1]["data"]
    assert data == {
        "previous_status": "done",
        "status": "in_progress",
        "actor": "resident",
        "comment": "Течёт",
    }


async def test_crm_outage_keeps_events_and_retries_with_backoff(world):
    integration, _ = await connect(world)
    world.webhooks.down = True
    first = await new_ticket(world, "Лифт")
    await new_ticket(world, "Ещё лифт")

    assert await deliver(world) == 0
    stored = await fresh(world, integration)
    assert stored.failures == 1 and stored.last_error
    assert stored.next_attempt_at == world.clock.now() + timedelta(seconds=10)
    assert await deliver(world) == 0  # not due yet: nothing is hammered

    world.webhooks.down = False
    world.clock.advance(timedelta(seconds=11))
    assert await deliver(world) == 2
    numbers = [envelope["ticket"]["number"] for _, envelope in world.webhooks.sent]
    assert numbers[0] == first.number and len(numbers) == 2
    stored = await fresh(world, integration)
    assert stored.failures == 0 and stored.last_error is None


async def test_event_rejected_as_invalid_is_skipped_not_retried(world):
    await connect(world)
    world.webhooks.status_code = 400
    await new_ticket(world)
    assert await deliver(world) == 1
    world.webhooks.status_code = 200
    assert await deliver(world) == 0


async def test_links_are_idempotent_and_one_record_belongs_to_one_ticket(world):
    integration, _ = await connect(world, webhook=False)
    first, second = await new_ticket(world), await new_ticket(world, "Другое")
    link = LinkTicketCommand(integration, first.number, ExternalRecord("R-1", "№1"))
    await world.services.integrations.link_ticket.execute(link)
    again = await world.services.integrations.link_ticket.execute(link)
    assert again.link is not None and again.link.external_number == "№1"
    with pytest.raises(ExternalIdTakenError):
        await world.services.integrations.link_ticket.execute(
            LinkTicketCommand(integration, second.number, ExternalRecord("R-1"))
        )


async def test_another_companys_ticket_is_invisible(world):
    integration, _ = await connect(world, webhook=False)
    other = ManagementCompany(uuid4(), "УО Другая", "+7", "Псков", True)
    house = Building(uuid4(), "psk900", "ул. Чужая, 9", other.id, True)
    world.store.companies[other.id] = other
    world.store.buildings[house.id] = house
    await world.services.bind_resident.execute(99, "psk900")
    foreign = await world.services.create_ticket.execute(
        CreateTicketCommand(99, None, "lift", False, "Чужой лифт")
    )
    with pytest.raises(TicketNotFoundError):
        await world.services.integrations.get_ticket.execute(
            integration, foreign.number
        )
    page = await world.services.integrations.list_events.execute(integration, 0, 50)
    assert page.events == ()


async def test_feed_and_ticket_list_page_without_gaps(world):
    integration, _ = await connect(world, webhook=False)
    for index in range(5):
        await new_ticket(world, f"Лифт {index}")
        world.clock.advance(timedelta(minutes=1))

    seen, after = [], 0
    while True:
        page = await world.services.integrations.list_events.execute(
            integration, after, 2
        )
        seen += [event["ticket"]["description"] for event in page.events]
        after = page.next_after
        if not page.has_more:
            break
    assert seen == [f"Лифт {index}" for index in range(5)]

    numbers, cursor = [], None
    while True:
        tickets = await world.services.integrations.list_tickets.execute(
            integration, cursor, 2
        )
        numbers += [item.view.number for item in tickets.tickets]
        if (cursor := tickets.next_cursor) is None:
            break
    assert numbers == sorted(numbers) and len(numbers) == 5


async def test_webhook_subscribes_to_chosen_event_types_only(world):
    integration, _ = await connect(world)
    await world.services.integrations.configure_webhook.execute(
        WebhookCommand(
            integration.id,
            HOOK,
            frozenset({IntegrationEventType.TICKET_STATUS_CHANGED}),
        )
    )
    ticket = await new_ticket(world)
    await world.services.change_status.execute(
        ChangeStatusCommand(
            ticket.id, TicketStatus.ACKNOWLEDGED, ActorRole.DISPATCHER, DISPATCHER
        )
    )
    await deliver(world)
    assert sent_types(world) == ["ticket.status_changed"]


async def test_sla_as_a_service(world):
    quote = world.services.integrations.calculate_sla.execute("lift", True)
    assert quote.react_by == world.clock.now() + timedelta(minutes=30)
    assert "416" in quote.legal_basis and not quote.warnings
    unknown = world.services.integrations.calculate_sla.execute("spaceship", False)
    assert unknown.category_code == "other" and unknown.warnings
