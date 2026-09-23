"""The reporter asks for a complaint to the housing inspection."""

from __future__ import annotations

from uuid import UUID

from application.errors import TicketNotFoundError
from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.chat_card import queue_card_refresh
from application.tickets.dto import TicketView
from domain.notifications.entities import Notification, NotificationKind


class EscalateTicket:
    """Checks the rule on the aggregate and queues the PDF for the bot to send.

    The document is built at delivery time from the current ticket state, so a
    repeated request always gets the latest timeline.
    """

    def __init__(
        self, uow_factory: UnitOfWorkFactory, queries: TicketQueries, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._clock = clock

    async def execute(self, ticket_id: UUID, user_id: int) -> TicketView:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            ticket = await uow.tickets.get(ticket_id)
            if ticket is None:
                raise TicketNotFoundError()
            ticket.escalate(user_id, now)
            await uow.tickets.save(ticket)
            await uow.outbox.add(
                Notification(
                    kind=NotificationKind.ESCALATION_DOCUMENT,
                    recipient_user_id=ticket.reporter_id,
                    ticket_id=ticket.id,
                    ticket_number=ticket.number,
                    status=ticket.status.value,
                    comment=None,
                    created_at=now,
                )
            )
            await queue_card_refresh(uow, ticket, now)
            await uow.commit()

        view = await self._queries.get(ticket_id, now)
        assert view is not None
        return view
