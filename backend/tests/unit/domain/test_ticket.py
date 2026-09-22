from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from domain.tickets.entities import Ticket
from domain.tickets.enums import ActorRole, TicketStatus
from domain.tickets.exceptions import NotTicketReporterError
from domain.tickets.responsibility import responsibility_for
from domain.tickets.sla import SlaPolicy

NOW = datetime(2026, 9, 23, 9, 0, tzinfo=UTC)
REPORTER = 42


def make_ticket() -> Ticket:
    return Ticket.register(
        sequence=42,
        building_id=uuid4(),
        company_id=uuid4(),
        reporter_id=REPORTER,
        chat_id=1000,
        category_code="lift",
        is_emergency=False,
        description="  Не работает лифт во 2 подъезде  ",
        responsibility=responsibility_for("lift"),
        deadlines=SlaPolicy().deadlines("lift", False, NOW),
        now=NOW,
    )


def test_registration_assigns_number_status_and_first_event():
    ticket = make_ticket()
    assert ticket.number == "2026-00042"
    assert ticket.status is TicketStatus.REGISTERED
    assert ticket.description == "Не работает лифт во 2 подъезде"
    assert [event.status for event in ticket.events] == [TicketStatus.REGISTERED]


def test_full_lifecycle_records_timeline():
    ticket = make_ticket()
    later = NOW + timedelta(hours=2)
    ticket.change_status(
        TicketStatus.IN_PROGRESS,
        actor_role=ActorRole.DISPATCHER,
        actor_id=7,
        now=later,
        comment=" мастер завтра к 10:00 ",
    )
    ticket.change_status(
        TicketStatus.DONE, actor_role=ActorRole.DISPATCHER, actor_id=7, now=later
    )
    ticket.change_status(
        TicketStatus.CONFIRMED,
        actor_role=ActorRole.RESIDENT,
        actor_id=REPORTER,
        now=later,
    )
    assert ticket.status is TicketStatus.CONFIRMED
    assert ticket.events[1].comment == "мастер завтра к 10:00"
    assert len(ticket.events) == 4
    assert ticket.updated_at == later


def test_other_resident_cannot_confirm():
    ticket = make_ticket()
    ticket.change_status(
        TicketStatus.DONE, actor_role=ActorRole.DISPATCHER, actor_id=7, now=NOW
    )
    with pytest.raises(NotTicketReporterError):
        ticket.change_status(
            TicketStatus.CONFIRMED, actor_role=ActorRole.RESIDENT, actor_id=99, now=NOW
        )


def test_overdue_only_while_open():
    ticket = make_ticket()
    after_deadline = ticket.deadlines.resolve_by + timedelta(minutes=1)
    assert ticket.is_overdue(after_deadline)
    ticket.change_status(
        TicketStatus.DONE, actor_role=ActorRole.DISPATCHER, actor_id=7, now=NOW
    )
    assert not ticket.is_overdue(after_deadline)
