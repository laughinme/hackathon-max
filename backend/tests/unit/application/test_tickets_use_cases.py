from datetime import timedelta
from uuid import uuid4

import pytest

from application.errors import TicketNotFoundError
from application.tickets.change_status import ChangeStatusCommand, ChangeTicketStatus
from application.tickets.create_ticket import CreateTicket, CreateTicketCommand
from application.tickets.queries import GetReporterTicket, ListReporterTickets
from application.tickets.triage_complaint import TriageComplaint
from domain.tickets.enums import ActorRole, ResponsibleParty, TicketStatus
from domain.tickets.sla import SlaPolicy
from infrastructure.memory.tickets import InMemoryTicketStore, InMemoryUnitOfWork
from tests.fakes import FixedClock, StaticClassifier, classification

REPORTER = 42


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def store() -> InMemoryTicketStore:
    return InMemoryTicketStore()


def uow_factory(store: InMemoryTicketStore):
    return lambda: InMemoryUnitOfWork(store)


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


async def test_create_ticket_sets_deadline_and_responsibility(store, clock):
    ticket = await CreateTicket(uow_factory(store), SlaPolicy(), clock).execute(
        command()
    )
    assert ticket.number == "2026-00001"
    assert ticket.status is TicketStatus.REGISTERED
    assert ticket.resolve_by == clock.now() + timedelta(days=1)
    assert ticket.responsible_party is ResponsibleParty.MANAGEMENT_COMPANY
    assert len(store.tickets) == 1


async def test_numbers_are_sequential(store, clock):
    create = CreateTicket(uow_factory(store), SlaPolicy(), clock)
    first = await create.execute(command())
    second = await create.execute(command())
    assert (first.number, second.number) == ("2026-00001", "2026-00002")


async def test_uncommitted_changes_are_discarded(store, clock):
    ticket = await CreateTicket(uow_factory(store), SlaPolicy(), clock).execute(
        command()
    )
    with pytest.raises(RuntimeError):
        async with InMemoryUnitOfWork(store) as uow:
            loaded = await uow.tickets.get(ticket.id)
            assert loaded is not None
            loaded.description = "changed"
            await uow.tickets.save(loaded)
            raise RuntimeError("boom")
    assert store.tickets[ticket.id].description == "Лифт стоит на 5 этаже"


async def test_change_status_and_overdue_flag(store, clock):
    created = await CreateTicket(uow_factory(store), SlaPolicy(), clock).execute(
        command()
    )
    clock.advance(timedelta(days=2))
    change = ChangeTicketStatus(uow_factory(store), clock)
    view = await change.execute(
        ChangeStatusCommand(
            ticket_id=created.id,
            target=TicketStatus.IN_PROGRESS,
            actor_role=ActorRole.DISPATCHER,
            actor_id=7,
            comment="мастер выехал",
        )
    )
    assert view.status is TicketStatus.IN_PROGRESS
    assert view.is_overdue
    assert view.events[-1].comment == "мастер выехал"


async def test_change_status_of_missing_ticket(store, clock):
    with pytest.raises(TicketNotFoundError):
        await ChangeTicketStatus(uow_factory(store), clock).execute(
            ChangeStatusCommand(
                ticket_id=uuid4(),
                target=TicketStatus.DONE,
                actor_role=ActorRole.DISPATCHER,
                actor_id=7,
            )
        )


async def test_reporter_sees_only_own_tickets(store, clock):
    create = CreateTicket(uow_factory(store), SlaPolicy(), clock)
    own = await create.execute(command())
    stranger = await create.execute(command(reporter_id=99))

    listed = await ListReporterTickets(uow_factory(store), clock).execute(REPORTER)
    assert [ticket.id for ticket in listed] == [own.id]

    get = GetReporterTicket(uow_factory(store), clock)
    assert (await get.execute(own.id, REPORTER)).id == own.id
    with pytest.raises(TicketNotFoundError):
        await get.execute(stranger.id, REPORTER)


async def test_triage_keeps_explicit_category_and_trusts_confident_model(clock):
    classifier = StaticClassifier(classification("water", emergency_confidence=0.95))
    triage = TriageComplaint(classifier, SlaPolicy(), clock, confidence_threshold=0.6)
    result = await triage.execute("лифт не едет", category_hint="lift")
    assert result.category_code == "lift"
    assert not result.is_emergency
    assert not result.needs_emergency_confirmation


async def test_triage_is_fail_safe_when_emergency_is_uncertain(clock):
    classifier = StaticClassifier(classification("water", emergency_confidence=0.4))
    triage = TriageComplaint(classifier, SlaPolicy(), clock, confidence_threshold=0.6)
    result = await triage.execute("что-то капает", category_hint=None)
    assert result.category_code == "water"
    assert result.is_emergency  # treated as emergency until the resident answers
    assert result.needs_emergency_confirmation
    assert result.deadlines_preview.react_by is not None

    confirmed = triage.preview("water", is_emergency=False)
    assert not confirmed.needs_emergency_confirmation
    assert confirmed.deadlines_preview.react_by is None
