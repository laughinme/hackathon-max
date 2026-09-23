"""Move a ticket along its lifecycle and notify the resident."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from application.errors import TicketNotFoundError
from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.chat_card import queue_card_refresh
from application.tickets.dto import TicketView
from domain.housing.exceptions import NotADispatcherError
from domain.notifications.entities import Notification, NotificationKind
from domain.tickets.enums import ActorRole, TicketStatus


@dataclass(frozen=True, slots=True)
class ChangeStatusCommand:
    ticket_id: UUID
    target: TicketStatus
    actor_role: ActorRole
    actor_id: int
    comment: str | None = None


class ChangeTicketStatus:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, queries: TicketQueries, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._clock = clock

    async def execute(self, command: ChangeStatusCommand) -> TicketView:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            ticket = await uow.tickets.get(command.ticket_id)
            if ticket is None:
                raise TicketNotFoundError()

            if command.actor_role is ActorRole.DISPATCHER:
                dispatcher = await uow.housing.get_dispatcher(command.actor_id)
                if dispatcher is None or dispatcher.company_id != ticket.company_id:
                    raise NotADispatcherError()

            event = ticket.change_status(
                command.target,
                actor_role=command.actor_role,
                actor_id=command.actor_id,
                now=now,
                comment=command.comment,
            )
            await uow.tickets.save(ticket)

            if command.actor_role is ActorRole.DISPATCHER:
                await uow.outbox.add(
                    Notification(
                        kind=NotificationKind.TICKET_STATUS_CHANGED,
                        recipient_user_id=ticket.reporter_id,
                        ticket_id=ticket.id,
                        ticket_number=ticket.number,
                        status=event.status.value,
                        comment=event.comment,
                        created_at=now,
                    )
                )
            await queue_card_refresh(uow, ticket, now)
            await uow.commit()

        view = await self._queries.get(ticket.id, now)
        assert view is not None
        return view
