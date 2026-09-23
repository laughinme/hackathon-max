"""Notifications to residents and dispatchers, written to the outbox in the same
transaction as the change that caused them and delivered later by a relay."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class NotificationKind(StrEnum):
    TICKET_STATUS_CHANGED = "ticket_status_changed"
    #: To the reporter: the legal deadline passed, a complaint is possible.
    TICKET_OVERDUE = "ticket_overdue"
    #: To every dispatcher of the company: the deadline passed.
    TICKET_OVERDUE_DISPATCHER = "ticket_overdue_dispatcher"
    #: To the reporter: the complaint to the housing inspection as a PDF.
    ESCALATION_DOCUMENT = "escalation_document"
    #: To the house chat (recipient is the chat id): redraw the ticket card.
    TICKET_CARD_REFRESH = "ticket_card_refresh"


@dataclass(frozen=True, slots=True)
class Notification:
    kind: NotificationKind
    recipient_user_id: int
    ticket_id: UUID
    ticket_number: str
    status: str
    comment: str | None
    created_at: datetime
    id: UUID = field(default_factory=uuid4)
