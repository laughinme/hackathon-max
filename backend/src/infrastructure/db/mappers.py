"""Explicit ORM <-> domain mapping for the ticket aggregate."""

from __future__ import annotations

from domain.tickets.entities import Ticket, TicketEvent
from domain.tickets.enums import ActorRole, ResponsibleParty, TicketStatus
from domain.tickets.sla import Deadlines
from infrastructure.db.models import TicketEventRow, TicketRow


def ticket_to_domain(row: TicketRow) -> Ticket:
    return Ticket(
        id=row.id,
        number=row.number,
        building_id=row.building_id,
        company_id=row.company_id,
        reporter_id=row.reporter_id,
        chat_id=row.chat_id,
        category_code=row.category_code,
        is_emergency=row.is_emergency,
        description=row.description,
        responsible_party=ResponsibleParty(row.responsible_party),
        responsibility_basis=row.responsibility_basis,
        deadlines=Deadlines(
            resolve_by=row.resolve_by,
            react_by=row.react_by,
            legal_basis=row.deadline_basis,
        ),
        status=TicketStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        events=[event_to_domain(event) for event in row.events],
        overdue_notified_at=row.overdue_notified_at,
        escalated_at=row.escalated_at,
    )


def event_to_domain(row: TicketEventRow) -> TicketEvent:
    return TicketEvent(
        status=TicketStatus(row.status),
        actor_role=ActorRole(row.actor_role),
        actor_id=row.actor_id,
        at=row.at,
        comment=row.comment,
    )


def ticket_to_row(ticket: Ticket) -> TicketRow:
    row = TicketRow(id=ticket.id, number=ticket.number)
    apply_ticket(row, ticket)
    return row


def apply_ticket(row: TicketRow, ticket: Ticket) -> None:
    """Copy mutable aggregate state onto a row; append events not yet stored."""

    row.building_id = ticket.building_id
    row.company_id = ticket.company_id
    row.reporter_id = ticket.reporter_id
    row.chat_id = ticket.chat_id
    row.category_code = ticket.category_code
    row.is_emergency = ticket.is_emergency
    row.description = ticket.description
    row.responsible_party = ticket.responsible_party.value
    row.responsibility_basis = ticket.responsibility_basis
    row.resolve_by = ticket.deadlines.resolve_by
    row.react_by = ticket.deadlines.react_by
    row.deadline_basis = ticket.deadlines.legal_basis
    row.status = ticket.status.value
    row.created_at = ticket.created_at
    row.updated_at = ticket.updated_at
    row.overdue_notified_at = ticket.overdue_notified_at
    row.escalated_at = ticket.escalated_at

    stored = len(row.events) if row.events else 0
    for position, event in enumerate(ticket.events[stored:], start=stored):
        row.events.append(
            TicketEventRow(
                position=position,
                status=event.status.value,
                actor_role=event.actor_role.value,
                actor_id=event.actor_id,
                at=event.at,
                comment=event.comment,
            )
        )
