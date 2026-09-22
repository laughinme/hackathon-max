"""Register a ticket with its legal deadline and responsible party."""

from __future__ import annotations

from dataclasses import dataclass

from application.ports.clock import Clock
from application.ports.tickets import UnitOfWorkFactory
from application.tickets.dto import TicketView, to_view
from domain.tickets.entities import Ticket
from domain.tickets.responsibility import responsibility_for
from domain.tickets.sla import SlaPolicy


@dataclass(frozen=True, slots=True)
class CreateTicketCommand:
    reporter_id: int
    chat_id: int | None
    category_code: str
    is_emergency: bool
    description: str


class CreateTicket:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, sla_policy: SlaPolicy, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._sla = sla_policy
        self._clock = clock

    async def execute(self, command: CreateTicketCommand) -> TicketView:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            ticket = Ticket.register(
                sequence=await uow.tickets.next_sequence(),
                reporter_id=command.reporter_id,
                chat_id=command.chat_id,
                category_code=command.category_code,
                is_emergency=command.is_emergency,
                description=command.description,
                responsibility=responsibility_for(command.category_code),
                deadlines=self._sla.deadlines(
                    command.category_code, command.is_emergency, now
                ),
                now=now,
            )
            await uow.tickets.add(ticket)
            await uow.commit()
        return to_view(ticket, now)
