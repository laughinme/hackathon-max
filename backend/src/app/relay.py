"""Background loops: deliver outbox notifications, detect overdue tickets."""

from __future__ import annotations

import asyncio
import logging

from application.notifications.deliver import DeliverNotifications
from application.tickets.detect_overdue import DetectOverdueTickets

logger = logging.getLogger(__name__)

IDLE_INTERVAL_SECONDS = 2.0
#: Deadlines are hours and days long; a minute of lag is invisible.
OVERDUE_INTERVAL_SECONDS = 60.0


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


async def run_overdue_watch(detect: DetectOverdueTickets) -> None:
    while True:
        try:
            found = await detect.execute()
            if found:
                logger.info("Overdue tickets reported: %s", found)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - keep the loop alive, retry next tick
            logger.exception("Overdue watch iteration failed")
            found = 0
        if not found:
            await asyncio.sleep(OVERDUE_INTERVAL_SECONDS)
