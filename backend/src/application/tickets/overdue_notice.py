"""Who is told when a ticket passes its legal deadline."""

from __future__ import annotations

from datetime import datetime

from application.ports.unit_of_work import UnitOfWork
from domain.notifications.entities import Notification, NotificationKind
from domain.tickets.entities import Ticket


async def queue_overdue_notices(uow: UnitOfWork, ticket: Ticket, now: datetime) -> None:
    """The reporter (with a complaint button) and every dispatcher of the company.

    Called inside the transaction that set `overdue_notified_at`.
    """

    recipients = [(ticket.reporter_id, NotificationKind.TICKET_OVERDUE)]
    recipients += [
        (dispatcher.max_user_id, NotificationKind.TICKET_OVERDUE_DISPATCHER)
        for dispatcher in await uow.housing.list_dispatchers(ticket.company_id)
    ]
    for recipient, kind in recipients:
        await uow.outbox.add(
            Notification(
                kind=kind,
                recipient_user_id=recipient,
                ticket_id=ticket.id,
                ticket_number=ticket.number,
                status=ticket.status.value,
                comment=None,
                created_at=now,
            )
        )
