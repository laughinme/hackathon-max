"""PostgreSQL outbox: writer inside a transaction, reader for the relay."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.ports.outbox import PendingNotification
from domain.notifications.entities import Notification, NotificationKind
from infrastructure.db.models import OutboxRow

#: A claimed row becomes due again after this lease if the relay crashes
#: before reporting the outcome (at-least-once delivery).
CLAIM_LEASE = timedelta(minutes=2)


def _payload(notification: Notification) -> dict:
    return {
        "ticket_id": str(notification.ticket_id),
        "ticket_number": notification.ticket_number,
        "status": notification.status,
        "comment": notification.comment,
    }


def _to_domain(row: OutboxRow) -> Notification:
    return Notification(
        id=row.id,
        kind=NotificationKind(row.kind),
        recipient_user_id=row.recipient_user_id,
        ticket_id=UUID(row.payload["ticket_id"]),
        ticket_number=row.payload["ticket_number"],
        status=row.payload["status"],
        comment=row.payload.get("comment"),
        created_at=row.created_at,
    )


class SqlOutbox:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, notification: Notification) -> None:
        self._session.add(
            OutboxRow(
                id=notification.id,
                kind=notification.kind.value,
                recipient_user_id=notification.recipient_user_id,
                payload=_payload(notification),
                created_at=notification.created_at,
                next_attempt_at=notification.created_at,
                attempts=0,
            )
        )


class SqlOutboxReader:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def claim_batch(self, limit: int, now: datetime) -> list[PendingNotification]:
        """Lock due rows (SKIP LOCKED) and lease them: another relay instance
        skips them, and after a crash they become due again when the lease ends."""

        async with self._session_factory() as session, session.begin():
            rows = (
                await session.scalars(
                    select(OutboxRow)
                    .where(
                        OutboxRow.sent_at.is_(None),
                        OutboxRow.next_attempt_at.is_not(None),
                        OutboxRow.next_attempt_at <= now,
                    )
                    .order_by(OutboxRow.created_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            claimed = [
                PendingNotification(_to_domain(row), row.attempts) for row in rows
            ]
            for row in rows:
                row.next_attempt_at = now + CLAIM_LEASE
        return claimed

    async def mark_sent(self, notification_id: UUID, now: datetime) -> None:
        await self._update(notification_id, sent_at=now, next_attempt_at=None)

    async def mark_failed(
        self, notification_id: UUID, error: str, retry_at: datetime | None
    ) -> None:
        await self._update(
            notification_id,
            attempts=OutboxRow.attempts + 1,
            last_error=error,
            next_attempt_at=retry_at,
        )

    async def _update(self, notification_id: UUID, **values: object) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                update(OutboxRow)
                .where(OutboxRow.id == notification_id)
                .values(**values)
            )
