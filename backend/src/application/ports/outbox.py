"""Transactional outbox: notifications are stored with the change that caused
them and delivered afterwards, so a MAX outage never loses or blocks a change."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from domain.notifications.entities import Notification


class Outbox(Protocol):
    """Write side, used inside a unit of work."""

    async def add(self, notification: Notification) -> None: ...


@dataclass(frozen=True, slots=True)
class PendingNotification:
    notification: Notification
    attempts: int


class OutboxReader(Protocol):
    """Delivery side, used by the relay outside of business transactions."""

    async def claim_batch(
        self, limit: int, now: datetime
    ) -> list[PendingNotification]: ...

    async def mark_sent(self, notification_id: UUID, now: datetime) -> None: ...

    async def mark_failed(
        self, notification_id: UUID, error: str, retry_at: datetime | None
    ) -> None: ...


class NotificationSender(Protocol):
    """Delivers one notification to the resident; raises on failure."""

    async def send(self, notification: Notification) -> None: ...
