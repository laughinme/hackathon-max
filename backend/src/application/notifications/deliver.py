"""Relay pending outbox notifications to residents with retries."""

from __future__ import annotations

import logging
from datetime import timedelta

from application.ports.clock import Clock
from application.ports.outbox import NotificationSender, OutboxReader

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
BACKOFF = (
    timedelta(seconds=10),
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=30),
)


class DeliverNotifications:
    def __init__(
        self, reader: OutboxReader, sender: NotificationSender, clock: Clock
    ) -> None:
        self._reader = reader
        self._sender = sender
        self._clock = clock

    async def execute(self, batch_size: int = 20) -> int:
        """Deliver one batch; returns how many were sent successfully."""

        sent = 0
        for pending in await self._reader.claim_batch(batch_size, self._clock.now()):
            notification = pending.notification
            try:
                await self._sender.send(notification)
            except Exception as exc:  # noqa: BLE001 - any delivery failure is retried
                attempt = pending.attempts + 1
                retry_at = (
                    self._clock.now() + BACKOFF[attempt - 1]
                    if attempt < MAX_ATTEMPTS
                    else None
                )
                logger.warning(
                    "Notification %s failed (attempt %s): %s",
                    notification.id,
                    attempt,
                    exc,
                )
                await self._reader.mark_failed(
                    notification.id, str(exc)[:500], retry_at
                )
            else:
                await self._reader.mark_sent(notification.id, self._clock.now())
                sent += 1
        return sent
