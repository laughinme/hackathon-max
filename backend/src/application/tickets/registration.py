"""One way to register a ticket, shared by the dialog and the house chat."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.ports.unit_of_work import UnitOfWork
from domain.housing.entities import Building
from domain.tickets.entities import Ticket
from domain.tickets.responsibility import responsibility_for
from domain.tickets.sla import SlaPolicy


@dataclass(frozen=True, slots=True)
class NewTicket:
    reporter_id: int
    chat_id: int | None
    category_code: str
    is_emergency: bool
    description: str


async def register_ticket(
    uow: UnitOfWork, sla: SlaPolicy, building: Building, new: NewTicket, now: datetime
) -> Ticket:
    """Builds the ticket with a fresh number. The caller finishes it (support,
    chat card) and only then adds it: repositories snapshot on `add`."""

    return Ticket.register(
        sequence=await uow.tickets.next_sequence(),
        building_id=building.id,
        company_id=building.company_id,
        reporter_id=new.reporter_id,
        chat_id=new.chat_id,
        category_code=new.category_code,
        is_emergency=new.is_emergency,
        description=new.description,
        responsibility=responsibility_for(new.category_code),
        deadlines=sla.deadlines(new.category_code, new.is_emergency, now),
        now=now,
    )
