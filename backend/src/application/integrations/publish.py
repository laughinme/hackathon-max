"""Record a ticket change for external systems, in the change's own transaction."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from application.integrations.payload import ticket_snapshot
from application.ports.unit_of_work import UnitOfWork
from application.tickets.dto import to_view
from domain.integrations.entities import IntegrationEvent, IntegrationEventType
from domain.tickets.entities import Ticket


async def publish_ticket_event(
    uow: UnitOfWork,
    ticket: Ticket,
    event_type: IntegrationEventType,
    now: datetime,
    data: dict[str, Any] | None = None,
) -> None:
    """Always recorded, even with nothing connected yet: a system connected
    later reads the history from the feed. Delivery is the relay's job, so a
    CRM outage never blocks or loses a change."""

    building = await uow.housing.get_building(ticket.building_id)
    address = building.address if building is not None else ""
    await uow.integration_events.add(
        IntegrationEvent(
            company_id=ticket.company_id,
            ticket_id=ticket.id,
            type=event_type,
            occurred_at=now,
            payload={
                "ticket": ticket_snapshot(to_view(ticket, now, address)),
                "data": data or {},
            },
        )
    )
