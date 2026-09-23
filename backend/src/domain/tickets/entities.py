"""Ticket aggregate: a registered problem with a legal deadline and a timeline."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from domain.tickets.enums import ActorRole, ResponsibleParty, TicketStatus
from domain.tickets.exceptions import NotTicketReporterError, TicketNotOverdueError
from domain.tickets.responsibility import Responsibility
from domain.tickets.sla import Deadlines
from domain.tickets.state_machine import OPEN, ensure_transition

#: Reporter id of a ticket whose author asked to delete their data: the ticket
#: stays with the company as a record about the building, nobody is notified.
ANONYMOUS_REPORTER = 0

DEMO_EXPIRED_AGO = timedelta(minutes=1)
DEMO_EXPIRED_COMMENT = (
    "Демо-режим: срок устранения перенесён в прошлое, чтобы показать эскалацию"
)


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
    building_id: UUID
    company_id: UUID
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
    #: When the resident and dispatchers were told the deadline had passed.
    overdue_notified_at: datetime | None = None
    #: When the reporter first asked for a complaint to the housing inspection.
    escalated_at: datetime | None = None

    @classmethod
    def register(
        cls,
        *,
        sequence: int,
        building_id: UUID,
        company_id: UUID,
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
            building_id=building_id,
            company_id=company_id,
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
    ) -> TicketEvent:
        ensure_transition(self.status, target, actor_role)
        if actor_role is ActorRole.RESIDENT and actor_id != self.reporter_id:
            raise NotTicketReporterError()

        event = TicketEvent(
            status=target,
            actor_role=actor_role,
            actor_id=actor_id,
            at=now,
            comment=comment.strip() if comment else None,
        )
        self.status = target
        self.updated_at = now
        self.events.append(event)
        return event

    @property
    def is_open(self) -> bool:
        return self.status in OPEN

    def is_overdue(self, now: datetime) -> bool:
        return self.is_open and now > self.deadlines.resolve_by

    def mark_overdue_notified(self, now: datetime) -> bool:
        """True once per ticket: the moment to tell people the deadline passed."""

        if self.overdue_notified_at is not None or not self.is_overdue(now):
            return False
        self.overdue_notified_at = now
        return True

    def expire_deadline_for_demo(self, now: datetime) -> None:
        """Move the deadline a minute into the past (demo mode only).

        Checkers cannot wait a day for a lift deadline. The shift is written
        to the timeline as a system event, so the card and the complaint PDF
        say openly that the deadline was moved. The caller guards demo mode.
        """

        expired = now - DEMO_EXPIRED_AGO
        react_by = self.deadlines.react_by
        self.deadlines = replace(
            self.deadlines,
            resolve_by=expired,
            react_by=min(react_by, expired) if react_by else None,
        )
        self.updated_at = now
        self.events.append(
            TicketEvent(
                status=self.status,
                actor_role=ActorRole.SYSTEM,
                actor_id=None,
                at=now,
                comment=DEMO_EXPIRED_COMMENT,
            )
        )

    def can_escalate(self, now: datetime) -> bool:
        return self.is_overdue(now)

    def escalate(self, actor_id: int, now: datetime) -> None:
        """The reporter asks for a complaint to the housing inspection.

        Allowed only while the ticket is open past its legal deadline: before
        that the company has not broken anything yet. Repeating it is fine
        (the resident may need the document again); the first time is kept.
        """

        if actor_id != self.reporter_id:
            raise NotTicketReporterError()
        if not self.can_escalate(now):
            raise TicketNotOverdueError()
        if self.escalated_at is None:
            self.escalated_at = now
