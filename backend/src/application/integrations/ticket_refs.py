"""How an external system points at a ticket: our id, our number or its own id.

`018f…` (UUID), `2026-00042` (number) or `ext:58391` (the system's record id,
after it was linked) — a CRM that only remembers its own ids never has to
store ours.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from application.errors import TicketNotFoundError
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWork
from domain.integrations.entities import Integration
from domain.tickets.entities import Ticket

EXTERNAL_PREFIX = "ext:"


async def resolve_ticket_id(
    ref: str,
    integration: Integration,
    uow: UnitOfWork,
    queries: TicketQueries,
    now: datetime,
) -> UUID:
    ref = ref.strip()
    if ref.startswith(EXTERNAL_PREFIX):
        link = await uow.integrations.find_link(
            integration.id, ref.removeprefix(EXTERNAL_PREFIX)
        )
        if link is None:
            raise TicketNotFoundError()
        return link.ticket_id
    try:
        return UUID(ref)
    except ValueError:
        pass
    view = await queries.get_by_number(ref, now)
    if view is None:
        raise TicketNotFoundError()
    return view.id


async def load_company_ticket(
    ref: str,
    integration: Integration,
    uow: UnitOfWork,
    queries: TicketQueries,
    now: datetime,
) -> Ticket:
    """Another company's ticket is reported as missing, not as forbidden."""

    ticket_id = await resolve_ticket_id(ref, integration, uow, queries, now)
    ticket = await uow.tickets.get(ticket_id)
    if ticket is None or ticket.company_id != integration.company_id:
        raise TicketNotFoundError()
    return ticket
