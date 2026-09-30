"""In-memory adapters of the integration ports, for the simulator and unit tests."""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from domain.integrations.entities import ExternalLink, Integration, IntegrationEvent

if TYPE_CHECKING:
    from infrastructure.memory.tickets import InMemoryStore, _Pending


class InMemoryIntegrationEventLog:
    def __init__(self, store: InMemoryStore, pending: _Pending) -> None:
        self._store = store
        self._pending = pending

    async def add(self, event: IntegrationEvent) -> None:
        self._store.event_seq += 1  # like a DB sequence: not rolled back
        seq = self._store.event_seq
        self._pending.put("events", seq, replace(event, seq=seq))

    async def latest_seq(self, company_id: UUID) -> int:
        seqs = [s for s, e in self._store.events.items() if e.company_id == company_id]
        return max(seqs, default=0)


class InMemoryIntegrationRepository:
    def __init__(self, store: InMemoryStore, pending: _Pending) -> None:
        self._store = store
        self._pending = pending

    async def add(self, integration: Integration) -> None:
        self._pending.put("integrations", integration.id, integration)

    async def get(self, integration_id: UUID) -> Integration | None:
        found = self._store.integrations.get(integration_id)
        return copy.deepcopy(found) if found else None

    async def get_by_key_hash(self, key_hash: str) -> Integration | None:
        found = next(
            (i for i in self._store.integrations.values() if i.key_hash == key_hash),
            None,
        )
        return copy.deepcopy(found) if found else None

    async def save(self, integration: Integration) -> None:
        self._pending.put("integrations", integration.id, integration)

    async def list_for_company(self, company_id: UUID) -> list[Integration]:
        found = [
            i for i in self._store.integrations.values() if i.company_id == company_id
        ]
        return [copy.deepcopy(i) for i in sorted(found, key=lambda i: i.created_at)]

    async def get_link(
        self, integration_id: UUID, ticket_id: UUID
    ) -> ExternalLink | None:
        found = self._store.links.get((integration_id, ticket_id))
        return copy.deepcopy(found) if found else None

    async def find_link(
        self, integration_id: UUID, external_id: str
    ) -> ExternalLink | None:
        found = next(
            (
                link
                for link in self._store.links.values()
                if link.integration_id == integration_id
                and link.external_id == external_id
            ),
            None,
        )
        return copy.deepcopy(found) if found else None

    async def save_link(self, link: ExternalLink) -> None:
        self._pending.put("links", (link.integration_id, link.ticket_id), link)


class InMemoryIntegrationFeed:
    LEASE = timedelta(minutes=2)

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def _after(self, company_id: UUID, after_seq: int) -> list[IntegrationEvent]:
        return [
            event
            for seq, event in sorted(self._store.events.items())
            if event.company_id == company_id and seq > after_seq
        ]

    async def claim_due_webhooks(self, now: datetime, limit: int) -> list[Integration]:
        claimed = []
        for integration in self._store.integrations.values():
            if len(claimed) >= limit:
                break
            due = (
                integration.next_attempt_at is None
                or integration.next_attempt_at <= now
            )
            if (
                integration.enabled
                and integration.webhook_url
                and due
                and self._after(integration.company_id, integration.delivered_seq)
            ):
                integration.next_attempt_at = now + self.LEASE
                claimed.append(copy.deepcopy(integration))
        return claimed

    async def events_after(
        self, company_id: UUID, after_seq: int, limit: int
    ) -> list[IntegrationEvent]:
        return self._after(company_id, after_seq)[:limit]

    async def links_for(
        self, integration_id: UUID, ticket_ids: list[UUID]
    ) -> dict[UUID, ExternalLink]:
        return {
            ticket_id: copy.deepcopy(link)
            for ticket_id in ticket_ids
            if (link := self._store.links.get((integration_id, ticket_id)))
        }

    async def pending_count(self, company_id: UUID, after_seq: int) -> int:
        return len(self._after(company_id, after_seq))

    async def record_progress(
        self, integration_id: UUID, delivered_seq: int, now: datetime
    ) -> None:
        integration = self._store.integrations[integration_id]
        if delivered_seq != integration.delivered_seq:
            integration.last_success_at = now
        integration.delivered_seq = delivered_seq
        integration.failures = 0
        integration.next_attempt_at = None
        integration.last_error = None

    async def record_failure(
        self, integration_id: UUID, error: str, retry_at: datetime
    ) -> None:
        integration = self._store.integrations[integration_id]
        integration.failures += 1
        integration.last_error = error
        integration.next_attempt_at = retry_at
