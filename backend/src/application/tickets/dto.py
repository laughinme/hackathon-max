"""Read models returned by ticket use cases to adapters (bot, HTTP API)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.tickets.entities import Ticket
from domain.tickets.enums import ActorRole, ResponsibleParty, TicketStatus
from domain.tickets.state_machine import OPEN


@dataclass(frozen=True, slots=True)
class TicketEventView:
    status: TicketStatus
    actor_role: ActorRole
    at: datetime
    comment: str | None


@dataclass(frozen=True, slots=True)
class TicketView:
    id: UUID
    number: str
    building_id: UUID
    building_address: str
    reporter_id: int
    company_id: UUID
    category_code: str
    is_emergency: bool
    description: str
    responsible_party: ResponsibleParty
    responsibility_basis: str
    status: TicketStatus
    resolve_by: datetime
    react_by: datetime | None
    deadline_basis: str
    is_overdue: bool
    created_at: datetime
    updated_at: datetime
    events: tuple[TicketEventView, ...]
    #: When the reporter asked for a complaint to the housing inspection.
    escalated_at: datetime | None = None
    #: The reporter may ask for the complaint now (open past the deadline).
    can_escalate: bool = False
    #: Neighbours who pressed "me too".
    supporter_ids: tuple[int, ...] = ()
    #: The house chat where the ticket card lives, if it was filed there.
    chat_id: int | None = None
    chat_card_mid: str | None = None

    @property
    def supporters_count(self) -> int:
        return len(self.supporter_ids)

    @property
    def is_open(self) -> bool:
        return self.status in OPEN


def to_view(ticket: Ticket, now: datetime, building_address: str) -> TicketView:
    return TicketView(
        id=ticket.id,
        number=ticket.number,
        building_id=ticket.building_id,
        building_address=building_address,
        reporter_id=ticket.reporter_id,
        company_id=ticket.company_id,
        category_code=ticket.category_code,
        is_emergency=ticket.is_emergency,
        description=ticket.description,
        responsible_party=ticket.responsible_party,
        responsibility_basis=ticket.responsibility_basis,
        status=ticket.status,
        resolve_by=ticket.deadlines.resolve_by,
        react_by=ticket.deadlines.react_by,
        deadline_basis=ticket.deadlines.legal_basis,
        is_overdue=ticket.is_overdue(now),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        events=tuple(
            TicketEventView(
                status=event.status,
                actor_role=event.actor_role,
                at=event.at,
                comment=event.comment,
            )
            for event in ticket.events
        ),
        escalated_at=ticket.escalated_at,
        can_escalate=ticket.can_escalate(now),
        supporter_ids=tuple(support.user_id for support in ticket.supporters),
        chat_id=ticket.chat_id,
        chat_card_mid=ticket.chat_card_mid,
    )
