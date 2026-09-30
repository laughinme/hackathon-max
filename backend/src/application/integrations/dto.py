"""Read models of the integration layer for adapters (REST, mini-app)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from application.tickets.dto import TicketView
from domain.integrations.entities import ExternalLink, Integration


@dataclass(frozen=True, slots=True)
class IntegrationView:
    id: UUID
    company_id: UUID
    name: str
    key_prefix: str
    enabled: bool
    created_at: datetime
    webhook_url: str | None
    event_types: tuple[str, ...]
    status_map: dict[str, str]
    delivered_seq: int
    #: Events the webhook has not delivered yet (0 without a webhook).
    pending_events: int
    last_success_at: datetime | None
    last_error: str | None
    next_attempt_at: datetime | None


def to_integration_view(integration: Integration, pending: int) -> IntegrationView:
    return IntegrationView(
        id=integration.id,
        company_id=integration.company_id,
        name=integration.name,
        key_prefix=integration.key_prefix,
        enabled=integration.enabled,
        created_at=integration.created_at,
        webhook_url=integration.webhook_url,
        event_types=tuple(sorted(t.value for t in integration.event_types)),
        status_map={code: ours.value for code, ours in integration.status_map.items()},
        delivered_seq=integration.delivered_seq,
        pending_events=pending,
        last_success_at=integration.last_success_at,
        last_error=integration.last_error,
        next_attempt_at=integration.next_attempt_at,
    )


@dataclass(frozen=True, slots=True)
class ExternalRecord:
    """The system's record for a ticket, as it reports it."""

    id: str
    number: str | None = None
    url: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class LinkedTicket:
    view: TicketView
    link: ExternalLink | None


@dataclass(frozen=True, slots=True)
class TicketPage:
    tickets: tuple[LinkedTicket, ...]
    #: Pass back as `cursor` for the next page; None when this page is the last.
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class EventPage:
    events: tuple[dict[str, Any], ...]
    #: Pass back as `after`; equal to the request's `after` when nothing is new.
    next_after: int
    has_more: bool
