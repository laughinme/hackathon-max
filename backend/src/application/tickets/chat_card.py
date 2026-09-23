"""Keep the ticket card in the house chat in step with the ticket."""

from __future__ import annotations

from datetime import datetime

from application.ports.unit_of_work import UnitOfWork
from domain.notifications.entities import Notification, NotificationKind
from domain.tickets.entities import Ticket


async def queue_card_refresh(uow: UnitOfWork, ticket: Ticket, now: datetime) -> None:
    """No-op for tickets filed in a private dialog: they have no card."""

    if ticket.chat_id is None or ticket.chat_card_mid is None:
        return
    await uow.outbox.add(
        Notification(
            kind=NotificationKind.TICKET_CARD_REFRESH,
            recipient_user_id=ticket.chat_id,
            ticket_id=ticket.id,
            ticket_number=ticket.number,
            status=ticket.status.value,
            comment=None,
            created_at=now,
        )
    )
