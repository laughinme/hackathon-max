"""Background loop that delivers outbox notifications."""

from __future__ import annotations

import asyncio
import logging

from application.notifications.deliver import DeliverNotifications

logger = logging.getLogger(__name__)

IDLE_INTERVAL_SECONDS = 2.0


async def run_relay(deliver: DeliverNotifications) -> None:
    while True:
        try:
            sent = await deliver.execute()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - keep the loop alive, retry next tick
            logger.exception("Notification relay iteration failed")
            sent = 0
        if sent == 0:
            await asyncio.sleep(IDLE_INTERVAL_SECONDS)
