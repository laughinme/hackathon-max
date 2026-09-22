"""Notifications to residents, written to the outbox in the same transaction
as the change that caused them and delivered later by a relay."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class NotificationKind(StrEnum):
    TICKET_STATUS_CHANGED = "ticket_status_changed"


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
