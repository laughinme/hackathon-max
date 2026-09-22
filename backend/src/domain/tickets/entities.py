"""Ticket aggregate: a registered problem with a legal deadline and a timeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from domain.tickets.enums import ActorRole, ResponsibleParty, TicketStatus
from domain.tickets.exceptions import NotTicketReporterError
from domain.tickets.responsibility import Responsibility
from domain.tickets.sla import Deadlines
from domain.tickets.state_machine import OPEN, ensure_transition


def format_ticket_number(year: int, sequence: int) -> str:
    """Human-readable number shown to residents: `2026-00042`."""

    return f"{year}-{sequence:05d}"


@dataclass(frozen=True, slots=True)
class TicketEvent:
    """One entry of the ticket timeline."""

    status: TicketStatus
    actor_role: ActorRole
    actor_id: int | None
    at: datetime
    comment: str | None = None


@dataclass(slots=True)
class Ticket:
    """A resident's problem registered with a deadline and a responsible party."""

    id: UUID
    number: str
    reporter_id: int
    chat_id: int | None
    category_code: str
    is_emergency: bool
    description: str
    responsible_party: ResponsibleParty
    responsibility_basis: str
    deadlines: Deadlines
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    events: list[TicketEvent] = field(default_factory=list)

    @classmethod
    def register(
        cls,
        *,
        sequence: int,
        reporter_id: int,
        chat_id: int | None,
        category_code: str,
        is_emergency: bool,
        description: str,
        responsibility: Responsibility,
        deadlines: Deadlines,
        now: datetime,
    ) -> Ticket:
        ticket = cls(
            id=uuid4(),
            number=format_ticket_number(now.year, sequence),
            reporter_id=reporter_id,
            chat_id=chat_id,
            category_code=category_code,
            is_emergency=is_emergency,
            description=description.strip(),
            responsible_party=responsibility.party,
            responsibility_basis=responsibility.legal_basis,
            deadlines=deadlines,
            status=TicketStatus.REGISTERED,
            created_at=now,
            updated_at=now,
        )
        ticket.events.append(
            TicketEvent(
                status=TicketStatus.REGISTERED,
                actor_role=ActorRole.RESIDENT,
                actor_id=reporter_id,
                at=now,
            )
        )
        return ticket

    def change_status(
        self,
        target: TicketStatus,
        *,
        actor_role: ActorRole,
        actor_id: int | None,
        now: datetime,
        comment: str | None = None,
    ) -> None:
        ensure_transition(self.status, target, actor_role)
        if actor_role is ActorRole.RESIDENT and actor_id != self.reporter_id:
            raise NotTicketReporterError()

        self.status = target
        self.updated_at = now
        self.events.append(
            TicketEvent(
                status=target,
                actor_role=actor_role,
                actor_id=actor_id,
                at=now,
                comment=comment.strip() if comment else None,
            )
        )

    @property
    def is_open(self) -> bool:
        return self.status in OPEN

    def is_overdue(self, now: datetime) -> bool:
        return self.is_open and now > self.deadlines.resolve_by
