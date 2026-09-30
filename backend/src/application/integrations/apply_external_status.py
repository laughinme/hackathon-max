"""The company's system moved a ticket: apply it here and tell the resident.

The system acts for the management company, so the move follows the
dispatcher's rules of the state machine. It cannot confirm a fix: only the
resident closes the loop. A repeated status is a no-op, so retries and
duplicated webhooks on the other side are safe.
"""

from __future__ import annotations

from dataclasses import dataclass

from application.integrations.dto import ExternalRecord, LinkedTicket
from application.integrations.link_ticket import upsert_link
from application.integrations.publish import publish_ticket_event
from application.integrations.ticket_refs import load_company_ticket
from application.ports.clock import Clock
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.chat_card import queue_card_refresh
from domain.integrations.entities import Integration, IntegrationEventType
from domain.notifications.entities import Notification, NotificationKind
from domain.tickets.enums import ActorRole


@dataclass(frozen=True, slots=True)
class ExternalStatusCommand:
    integration: Integration
    ticket_ref: str
    #: The system's own code (mapped by the status map) or ours.
    status: str
    comment: str | None = None
    #: Link the system's record in the same call.
    record: ExternalRecord | None = None


@dataclass(frozen=True, slots=True)
class ExternalStatusResult:
    ticket: LinkedTicket
    #: False when the ticket already had this status (nothing changed).
    applied: bool


class ApplyExternalStatus:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, queries: TicketQueries, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._clock = clock

    async def execute(self, command: ExternalStatusCommand) -> ExternalStatusResult:
        integration = command.integration
        target = integration.to_status(command.status)
        now = self._clock.now()
        async with self._uow_factory() as uow:
            ticket = await load_company_ticket(
                command.ticket_ref, integration, uow, self._queries, now
            )
            previous = ticket.status
            applied = previous is not target
            if applied:
                event = ticket.change_status(
                    target,
                    actor_role=ActorRole.DISPATCHER,
                    actor_id=None,
                    now=now,
                    comment=command.comment,
                )
                await uow.tickets.save(ticket)
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
                await publish_ticket_event(
                    uow,
                    ticket,
                    IntegrationEventType.TICKET_STATUS_CHANGED,
                    now,
                    {
                        "previous_status": previous.value,
                        "status": target.value,
                        "actor": "integration",
                        "comment": event.comment,
                        "source_integration_id": str(integration.id),
                    },
                )

            record = command.record
            link = await uow.integrations.get_link(integration.id, ticket.id)
            if record is None and link is not None:
                record = ExternalRecord(id=link.external_id)
            if record is not None:
                record = ExternalRecord(
                    id=record.id,
                    number=record.number,
                    url=record.url,
                    status=command.status.strip(),
                )
                link = await upsert_link(uow, integration.id, ticket.id, record, now)
            await uow.commit()

        view = await self._queries.get(ticket.id, now)
        assert view is not None
        return ExternalStatusResult(LinkedTicket(view, link), applied)
