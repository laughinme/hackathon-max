from datetime import timedelta
from uuid import uuid4

import pytest

from application.errors import TicketNotFoundError
from application.tickets.change_status import ChangeStatusCommand
from application.tickets.create_ticket import CreateTicketCommand
from application.tickets.triage_complaint import TriageComplaint
from domain.housing.exceptions import NotADispatcherError, ResidentNotBoundError
from domain.tickets.enums import ActorRole, ResponsibleParty, TicketStatus
from domain.tickets.sla import SlaPolicy
from tests.fakes import FixedClock, StaticClassifier, World, classification, make_world

REPORTER = 42
DISPATCHER = 7


@pytest.fixture
async def world() -> World:
    world = make_world()
    await world.services.bind_resident.execute(REPORTER, "psk001")
    world.add_dispatcher(DISPATCHER)
    return world


def command(**overrides) -> CreateTicketCommand:
    values = dict(
        reporter_id=REPORTER,
        chat_id=1000,
        category_code="lift",
        is_emergency=False,
        description="Лифт стоит на 5 этаже",
    )
    values.update(overrides)
    return CreateTicketCommand(**values)


def status(
    ticket_id, target, role=ActorRole.DISPATCHER, actor=DISPATCHER, comment=None
):
    return ChangeStatusCommand(ticket_id, target, role, actor, comment)


async def test_create_ticket_binds_building_deadline_and_responsibility(world):
    ticket = await world.services.create_ticket.execute(command())
    assert ticket.number == "2026-00001"
    assert ticket.building_address == "ул. Тестовая, 1"
    assert ticket.company_id == world.company.id
    assert ticket.resolve_by == world.clock.now() + timedelta(days=1)
    assert ticket.responsible_party is ResponsibleParty.MANAGEMENT_COMPANY


async def test_resident_without_building_cannot_create(world):
    with pytest.raises(ResidentNotBoundError):
        await world.services.create_ticket.execute(command(reporter_id=999))


async def test_dispatcher_change_notifies_reporter_in_same_transaction(world):
    created = await world.services.create_ticket.execute(command())
    view = await world.services.change_status.execute(
        status(created.id, TicketStatus.IN_PROGRESS, comment="мастер выехал")
    )
    assert view.status is TicketStatus.IN_PROGRESS
    [entry] = world.store.outbox.values()
    assert entry.notification.recipient_user_id == REPORTER
    assert entry.notification.comment == "мастер выехал"
    assert entry.notification.ticket_number == created.number


async def test_resident_confirmation_does_not_notify_themselves(world):
    created = await world.services.create_ticket.execute(command())
    await world.services.change_status.execute(status(created.id, TicketStatus.DONE))
    await world.services.change_status.execute(
        status(created.id, TicketStatus.CONFIRMED, ActorRole.RESIDENT, REPORTER)
    )
    assert len(world.store.outbox) == 1  # only the dispatcher's "done"


async def test_stranger_cannot_act_as_dispatcher(world):
    created = await world.services.create_ticket.execute(command())
    with pytest.raises(NotADispatcherError):
        await world.services.change_status.execute(
            status(created.id, TicketStatus.DONE, actor=555)
        )
    assert not world.store.outbox


async def test_missing_ticket(world):
    with pytest.raises(TicketNotFoundError):
        await world.services.change_status.execute(status(uuid4(), TicketStatus.DONE))


async def test_ticket_visible_to_reporter_and_company_dispatcher_only(world):
    created = await world.services.create_ticket.execute(command())
    get = world.services.get_ticket
    assert (await get.execute(created.id, REPORTER)).id == created.id
    assert (await get.execute(created.id, DISPATCHER)).id == created.id
    with pytest.raises(TicketNotFoundError):
        await get.execute(created.id, 555)


async def test_queue_orders_open_tickets_by_deadline(world):
    routine = await world.services.create_ticket.execute(command(category_code="light"))
    urgent = await world.services.create_ticket.execute(command(is_emergency=True))
    queue = await world.services.list_queue.execute(DISPATCHER)
    assert [ticket.id for ticket in queue] == [urgent.id, routine.id]
    with pytest.raises(NotADispatcherError):
        await world.services.list_queue.execute(REPORTER)


async def test_overdue_flag(world):
    created = await world.services.create_ticket.execute(command())
    world.clock.advance(timedelta(days=2))
    [view] = await world.services.list_tickets.execute(REPORTER)
    assert view.id == created.id and view.is_overdue


async def test_triage_keeps_explicit_category_and_trusts_confident_model():
    classifier = StaticClassifier(classification("water", emergency_confidence=0.95))
    triage = TriageComplaint(classifier, SlaPolicy(), FixedClock(), 0.6)
    result = await triage.execute("лифт не едет", category_hint="lift")
    assert result.category_code == "lift"
    assert not result.is_emergency and not result.needs_emergency_confirmation


async def test_triage_is_fail_safe_when_emergency_is_uncertain():
    classifier = StaticClassifier(classification("water", emergency_confidence=0.4))
    triage = TriageComplaint(classifier, SlaPolicy(), FixedClock(), 0.6)
    result = await triage.execute("что-то капает", category_hint=None)
    assert result.is_emergency and result.needs_emergency_confirmation
    assert result.deadlines_preview.react_by is not None
    assert (
        triage.preview("water", is_emergency=False).deadlines_preview.react_by is None
    )
