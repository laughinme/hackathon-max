"""Two numbers, one ticket: remember the system's record for our ticket."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from application.integrations.dto import ExternalRecord, LinkedTicket
from application.integrations.ticket_refs import load_company_ticket
from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory
from domain.integrations.entities import ExternalLink, Integration
from domain.integrations.exceptions import ExternalIdTakenError


async def upsert_link(
    uow: UnitOfWork,
    integration_id: UUID,
    ticket_id: UUID,
    record: ExternalRecord,
    now: datetime,
) -> ExternalLink:
    """Idempotent: the same record again changes nothing. Fields left empty
    keep their values; one record never belongs to two tickets."""

    taken = await uow.integrations.find_link(integration_id, record.id)
    if taken is not None and taken.ticket_id != ticket_id:
        raise ExternalIdTakenError(record.id)

    link = await uow.integrations.get_link(integration_id, ticket_id)
    if link is None:
        link = ExternalLink(
            integration_id=integration_id,
            ticket_id=ticket_id,
            external_id=record.id,
            updated_at=now,
        )
    link.external_id = record.id
    link.external_number = record.number or link.external_number
    link.external_url = record.url or link.external_url
    link.external_status = record.status or link.external_status
    link.updated_at = now
    await uow.integrations.save_link(link)
    return link


@dataclass(frozen=True, slots=True)
class LinkTicketCommand:
    integration: Integration
    ticket_ref: str
    record: ExternalRecord


class LinkExternalTicket:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, queries: TicketQueries, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._clock = clock

    async def execute(self, command: LinkTicketCommand) -> LinkedTicket:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            ticket = await load_company_ticket(
                command.ticket_ref, command.integration, uow, self._queries, now
            )
            link = await upsert_link(
                uow, command.integration.id, ticket.id, command.record, now
            )
            await uow.commit()

        view = await self._queries.get(ticket.id, now)
        assert view is not None
        return LinkedTicket(view, link)
