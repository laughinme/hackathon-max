"""Delivers outbox notifications to residents and dispatchers as MAX messages."""

from __future__ import annotations

import asyncio
import logging
import time

from maxapi import Bot
from maxapi.enums.upload_type import UploadType
from maxapi.types.input_media import InputMediaBuffer

from application.tickets.build_escalation_document import BuildEscalationDocument
from bot import dispatcher_keyboards
from bot.presenters import STATUS_LABELS
from domain.notifications.entities import Notification, NotificationKind
from domain.tickets.enums import TicketStatus

logger = logging.getLogger(__name__)

#: MAX allows 2 messages per second into one chat.
MIN_INTERVAL_PER_CHAT = 0.5


def render(notification: Notification) -> str:
    number = notification.ticket_number
    match notification.kind:
        case NotificationKind.TICKET_OVERDUE:
            return (
                f"🚨 <b>Заявка № {number}: нормативный срок истёк</b>\n\n"
                "Управляющая организация не устранила проблему вовремя. Я могу "
                "подготовить жалобу в жилищную инспекцию: факты и история заявки "
                "уже внутри, останется вписать свои данные и подписать."
            )
        case NotificationKind.TICKET_OVERDUE_DISPATCHER:
            return (
                f"🚨 <b>Просрочена заявка № {number}</b>\n"
                f"Статус: {STATUS_LABELS[TicketStatus(notification.status)]}\n\n"
                "Житель может подать жалобу в жилищную инспекцию."
            )
        case NotificationKind.ESCALATION_DOCUMENT:
            return (
                f"📄 <b>Жалоба в жилищную инспекцию по заявке № {number}</b>\n\n"
                "Проверьте текст, впишите ФИО и адрес для ответа, подпишите и "
                "подайте в инспекцию вашего региона: лично, почтой или через её "
                "электронную приёмную. Ответ по закону — в течение 30 дней."
            )
        case NotificationKind.TICKET_STATUS_CHANGED:
            status = TicketStatus(notification.status)
            lines = [
                f"🔔 <b>Заявка № {number}</b>",
                f"Новый статус: {STATUS_LABELS[status]}",
            ]
            if notification.comment:
                lines.append(f"Комментарий УО: {notification.comment}")
            if status is TicketStatus.DONE:
                lines += ["", "Проблема устранена?"]
            return "\n".join(lines)


class MaxNotificationSender:
    def __init__(self, bot: Bot, documents: BuildEscalationDocument) -> None:
        self._bot = bot
        self._documents = documents
        self._last_sent: dict[int, float] = {}

    async def send(self, notification: Notification) -> None:
        recipient = notification.recipient_user_id
        if recipient <= 0:  # synthetic demo user, nobody to message
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
            attachments=await self._attachments(notification),
        )
        self._last_sent[recipient] = time.monotonic()

    async def _attachments(self, notification: Notification) -> list:
        ticket_id = notification.ticket_id
        match notification.kind:
            case NotificationKind.TICKET_OVERDUE:
                return [dispatcher_keyboards.overdue_for_resident(ticket_id)]
            case NotificationKind.TICKET_OVERDUE_DISPATCHER:
                return [dispatcher_keyboards.overdue_for_dispatcher(ticket_id)]
            case NotificationKind.ESCALATION_DOCUMENT:
                document = await self._documents.execute(ticket_id)
                return [
                    InputMediaBuffer(
                        document.content,
                        filename=document.filename,
                        type=UploadType.FILE,
                    )
                ]
            case NotificationKind.TICKET_STATUS_CHANGED:
                return [
                    dispatcher_keyboards.notification(
                        ticket_id, TicketStatus(notification.status)
                    )
                ]
