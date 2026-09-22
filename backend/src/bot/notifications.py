"""Delivers outbox notifications to residents as MAX messages."""

from __future__ import annotations

import asyncio
import logging
import time

from maxapi import Bot

from bot import dispatcher_keyboards
from bot.presenters import STATUS_LABELS
from domain.notifications.entities import Notification
from domain.tickets.enums import TicketStatus

logger = logging.getLogger(__name__)

#: MAX allows 2 messages per second into one chat.
MIN_INTERVAL_PER_CHAT = 0.5


def render(notification: Notification) -> str:
    status = TicketStatus(notification.status)
    lines = [
        f"🔔 <b>Заявка № {notification.ticket_number}</b>",
        f"Новый статус: {STATUS_LABELS[status]}",
    ]
    if notification.comment:
        lines.append(f"Комментарий УО: {notification.comment}")
    if status is TicketStatus.DONE:
        lines += ["", "Проблема устранена?"]
    return "\n".join(lines)


class MaxNotificationSender:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot
        self._last_sent: dict[int, float] = {}

    async def send(self, notification: Notification) -> None:
        recipient = notification.recipient_user_id
        if recipient <= 0:  # synthetic demo resident, nobody to message
            logger.info("Skip notification to synthetic user %s", recipient)
            return

        wait = MIN_INTERVAL_PER_CHAT - (
            time.monotonic() - self._last_sent.get(recipient, 0)
        )
        if wait > 0:
            await asyncio.sleep(wait)
        await self._bot.send_message(
            user_id=recipient,
            text=render(notification),
            attachments=[
                dispatcher_keyboards.notification(
                    notification.ticket_id, TicketStatus(notification.status)
                )
            ],
        )
        self._last_sent[recipient] = time.monotonic()
