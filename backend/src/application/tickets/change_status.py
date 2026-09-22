"""Move a ticket along its lifecycle (dispatcher actions, resident confirmation)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from application.errors import TicketNotFoundError
from application.ports.clock import Clock
from application.ports.tickets import UnitOfWorkFactory
from application.tickets.dto import TicketView, to_view
from domain.tickets.enums import ActorRole, TicketStatus


@dataclass(frozen=True, slots=True)
class ChangeStatusCommand:
    ticket_id: UUID
    target: TicketStatus
    actor_role: ActorRole
    actor_id: int | None
    comment: str | None = None


class ChangeTicketStatus:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, command: ChangeStatusCommand) -> TicketView:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            ticket = await uow.tickets.get(command.ticket_id)
            if ticket is None:
                raise TicketNotFoundError()
            ticket.change_status(
                command.target,
                actor_role=command.actor_role,
                actor_id=command.actor_id,
                now=now,
                comment=command.comment,
            )
            await uow.tickets.save(ticket)
            await uow.commit()
        return to_view(ticket, now)
