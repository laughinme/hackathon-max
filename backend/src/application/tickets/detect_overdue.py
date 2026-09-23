"""Find tickets that just passed their legal deadline and tell people once."""

from __future__ import annotations

from application.ports.clock import Clock
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.notifications.entities import Notification, NotificationKind

BATCH_SIZE = 50


class DetectOverdueTickets:
    """The reporter learns a complaint is now possible; every dispatcher of the
    company learns the deadline is blown. Marks and notifications are written
    in one transaction, so a crash never notifies twice or loses a ticket."""

    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self) -> int:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            tickets = await uow.tickets.list_overdue_unnotified(now, BATCH_SIZE)
            for ticket in tickets:
                if not ticket.mark_overdue_notified(now):
                    continue
                await uow.tickets.save(ticket)

                recipients = [(ticket.reporter_id, NotificationKind.TICKET_OVERDUE)]
                recipients += [
                    (dispatcher.max_user_id, NotificationKind.TICKET_OVERDUE_DISPATCHER)
                    for dispatcher in await uow.housing.list_dispatchers(
                        ticket.company_id
                    )
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
            await uow.commit()
        return len(tickets)
