"""Register a resident's ticket with its legal deadline and responsible party."""

from __future__ import annotations

from dataclasses import dataclass

from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.dto import TicketView
from application.tickets.registration import NewTicket, register_ticket
from domain.housing.exceptions import BuildingNotFoundError, ResidentNotBoundError
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
        self,
        uow_factory: UnitOfWorkFactory,
        queries: TicketQueries,
        sla_policy: SlaPolicy,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._sla = sla_policy
        self._clock = clock

    async def execute(self, command: CreateTicketCommand) -> TicketView:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            resident = await uow.housing.get_resident(command.reporter_id)
            if resident is None:
                raise ResidentNotBoundError()
            building = await uow.housing.get_building(resident.building_id)
            if building is None:
                raise BuildingNotFoundError()

            ticket = await register_ticket(
                uow,
                self._sla,
                building,
                NewTicket(
                    reporter_id=command.reporter_id,
                    chat_id=command.chat_id,
                    category_code=command.category_code,
                    is_emergency=command.is_emergency,
                    description=command.description,
                ),
                now,
            )
            await uow.tickets.add(ticket)
            await uow.commit()

        view = await self._queries.get(ticket.id, now)
        assert view is not None, "ticket must be readable right after commit"
        return view
