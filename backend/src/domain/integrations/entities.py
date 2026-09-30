"""Connections to a management company's own systems: CRM, 1C, dispatch service.

One connection speaks one contract, whatever is on the other side: signed
webhooks out, a cursor feed of the same events, and a small REST API in. The
only per-system part is data: which events to send and how the system's own
status codes map to ours.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from domain.integrations.exceptions import UnknownExternalStatusError
from domain.tickets.enums import TicketStatus


class IntegrationEventType(StrEnum):
    TICKET_CREATED = "ticket.created"
    #: Any move: dispatcher, CRM, the resident confirming or reopening.
    TICKET_STATUS_CHANGED = "ticket.status_changed"
    #: A neighbour pressed "me too": the problem affects more flats.
    TICKET_SUPPORTED = "ticket.supported"
    #: The legal deadline passed while the ticket is still open.
    TICKET_OVERDUE = "ticket.overdue"
    #: The reporter asked for a complaint to the housing inspection.
    TICKET_ESCALATED = "ticket.escalated"


ALL_EVENT_TYPES: frozenset[IntegrationEventType] = frozenset(IntegrationEventType)


@dataclass(frozen=True, slots=True)
class IntegrationEvent:
    """A fact about a ticket, stored with the change in one transaction.

    `seq` is the position in the company's feed, assigned on storage.
    `payload` is JSON-ready: the ticket as it was at `occurred_at` and the
    event's own data.
    """

    company_id: UUID
    ticket_id: UUID
    type: IntegrationEventType
    occurred_at: datetime
    payload: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    seq: int | None = None

    @property
    def source_integration_id(self) -> str | None:
        """Set when the change came from an integration: never echo it back."""

        return self.payload.get("data", {}).get("source_integration_id")


@dataclass(slots=True)
class Integration:
    """One connected system of a management company, with its API key."""

    id: UUID
    company_id: UUID
    name: str
    #: First characters of the key, to tell keys apart in the UI.
    key_prefix: str
    key_hash: str
    created_at: datetime
    enabled: bool = True
    webhook_url: str | None = None
    webhook_secret: str | None = None
    event_types: frozenset[IntegrationEventType] = ALL_EVENT_TYPES
    #: The system's own status codes -> ours, e.g. {"WORKING": in_progress}.
    status_map: dict[str, TicketStatus] = field(default_factory=dict)
    #: Webhook delivery: last delivered feed position and retry state.
    delivered_seq: int = 0
    failures: int = 0
    next_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None

    def wants(self, event: IntegrationEvent) -> bool:
        """Subscribed to this type and not the echo of its own change."""

        return event.type in self.event_types and event.source_integration_id != str(
            self.id
        )

    def to_status(self, raw: str) -> TicketStatus:
        """Our status for a code the system sent: its own code or ours.

        An unknown code is refused rather than guessed: a wrong status
        would reach the resident.
        """

        code = raw.strip()
        if code in self.status_map:
            return self.status_map[code]
        try:
            return TicketStatus(code.lower())
        except ValueError:
            raise UnknownExternalStatusError(raw) from None

    def external_status(self, status: TicketStatus) -> str | None:
        """The system's code for our status, when the map has one."""

        return next(
            (code for code, ours in self.status_map.items() if ours is status), None
        )


@dataclass(slots=True)
class ExternalLink:
    """Two numbers, one ticket: our ticket and its record in the system."""

    integration_id: UUID
    ticket_id: UUID
    external_id: str
    updated_at: datetime
    external_number: str | None = None
    external_url: str | None = None
    external_status: str | None = None
