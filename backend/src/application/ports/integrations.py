"""Ports of the integration layer: storage, the event feed and webhook delivery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from domain.integrations.entities import ExternalLink, Integration, IntegrationEvent


class IntegrationEventLog(Protocol):
    """Write side, inside the unit of work that changed the ticket."""

    async def add(self, event: IntegrationEvent) -> None: ...

    async def latest_seq(self, company_id: UUID) -> int:
        """Feed position of the company's newest event, 0 when there is none."""
        ...


class IntegrationRepository(Protocol):
    """Connections and ticket links, inside a unit of work."""

    async def add(self, integration: Integration) -> None: ...

    async def get(self, integration_id: UUID) -> Integration | None: ...

    async def get_by_key_hash(self, key_hash: str) -> Integration | None: ...

    async def save(self, integration: Integration) -> None:
        """Settings only; delivery state is written by `IntegrationFeed`."""
        ...

    async def list_for_company(self, company_id: UUID) -> list[Integration]: ...

    async def get_link(
        self, integration_id: UUID, ticket_id: UUID
    ) -> ExternalLink | None: ...

    async def find_link(
        self, integration_id: UUID, external_id: str
    ) -> ExternalLink | None: ...

    async def save_link(self, link: ExternalLink) -> None: ...


class IntegrationFeed(Protocol):
    """Read side of the event feed and webhook delivery state, outside business
    transactions (like the notification outbox reader)."""

    async def claim_due_webhooks(self, now: datetime, limit: int) -> list[Integration]:
        """Enabled webhooks with undelivered events whose retry time has come,
        leased so a second relay skips them."""
        ...

    async def events_after(
        self, company_id: UUID, after_seq: int, limit: int
    ) -> list[IntegrationEvent]:
        """Committed events in feed order, oldest first."""
        ...

    async def links_for(
        self, integration_id: UUID, ticket_ids: list[UUID]
    ) -> dict[UUID, ExternalLink]: ...

    async def pending_count(self, company_id: UUID, after_seq: int) -> int: ...

    async def record_progress(
        self, integration_id: UUID, delivered_seq: int, now: datetime
    ) -> None:
        """Delivered up to `delivered_seq`: clear the failure state."""
        ...

    async def record_failure(
        self, integration_id: UUID, error: str, retry_at: datetime
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class WebhookResponse:
    status_code: int
    #: Parsed JSON object of the answer, when there was one.
    body: dict[str, Any] | None


class WebhookSender(Protocol):
    async def send(
        self, url: str, secret: str, envelope: dict[str, Any]
    ) -> WebhookResponse:
        """POST the signed envelope; raises on network errors and timeouts."""
        ...

    def check_url(self, url: str) -> None:
        """Raise `WebhookUrlRejectedError` for a URL we must not call."""
        ...
