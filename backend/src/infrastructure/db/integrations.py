"""SQL adapters of the integration write side: connections, links, event log."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.integrations.entities import (
    ExternalLink,
    Integration,
    IntegrationEvent,
    IntegrationEventType,
)
from domain.tickets.enums import TicketStatus
from infrastructure.db.integration_models import (
    ExternalTicketLinkRow,
    IntegrationEventRow,
    IntegrationRow,
)


def integration_to_domain(row: IntegrationRow) -> Integration:
    return Integration(
        id=row.id,
        company_id=row.company_id,
        name=row.name,
        key_prefix=row.key_prefix,
        key_hash=row.key_hash,
        created_at=row.created_at,
        enabled=row.enabled,
        webhook_url=row.webhook_url,
        webhook_secret=row.webhook_secret,
        event_types=frozenset(IntegrationEventType(t) for t in row.event_types),
        status_map={code: TicketStatus(ours) for code, ours in row.status_map.items()},
        delivered_seq=row.delivered_seq,
        failures=row.failures,
        next_attempt_at=row.next_attempt_at,
        last_success_at=row.last_success_at,
        last_error=row.last_error,
    )


def apply_settings(row: IntegrationRow, integration: Integration) -> None:
    """Settings only: delivery state belongs to the relay (`SqlIntegrationFeed`),
    except when the webhook is (re)started, which resets the cursor."""

    row.name = integration.name
    row.enabled = integration.enabled
    row.webhook_secret = integration.webhook_secret
    row.event_types = sorted(t.value for t in integration.event_types)
    row.status_map = {code: ours.value for code, ours in integration.status_map.items()}
    if row.webhook_url is None and integration.webhook_url is not None:
        row.delivered_seq = integration.delivered_seq
        row.failures = integration.failures
        row.next_attempt_at = integration.next_attempt_at
        row.last_error = integration.last_error
    row.webhook_url = integration.webhook_url


def link_to_domain(row: ExternalTicketLinkRow) -> ExternalLink:
    return ExternalLink(
        integration_id=row.integration_id,
        ticket_id=row.ticket_id,
        external_id=row.external_id,
        updated_at=row.updated_at,
        external_number=row.external_number,
        external_url=row.external_url,
        external_status=row.external_status,
    )


def event_to_domain(row: IntegrationEventRow) -> IntegrationEvent:
    return IntegrationEvent(
        id=row.id,
        seq=row.seq,
        company_id=row.company_id,
        ticket_id=row.ticket_id,
        type=IntegrationEventType(row.type),
        occurred_at=row.occurred_at,
        payload=row.payload,
    )


class SqlIntegrationEventLog:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: IntegrationEvent) -> None:
        self._session.add(
            IntegrationEventRow(
                id=event.id,
                company_id=event.company_id,
                ticket_id=event.ticket_id,
                type=event.type.value,
                occurred_at=event.occurred_at,
                payload=event.payload,
            )
        )

    async def latest_seq(self, company_id: UUID) -> int:
        value = await self._session.scalar(
            select(func.max(IntegrationEventRow.seq)).where(
                IntegrationEventRow.company_id == company_id
            )
        )
        return int(value or 0)


class SqlIntegrationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, integration: Integration) -> None:
        row = IntegrationRow(
            id=integration.id,
            company_id=integration.company_id,
            key_prefix=integration.key_prefix,
            key_hash=integration.key_hash,
            created_at=integration.created_at,
            webhook_url=None,
            delivered_seq=integration.delivered_seq,
            failures=integration.failures,
            next_attempt_at=integration.next_attempt_at,
            last_success_at=integration.last_success_at,
            last_error=integration.last_error,
        )
        apply_settings(row, integration)
        self._session.add(row)

    async def get(self, integration_id: UUID) -> Integration | None:
        row = await self._session.get(IntegrationRow, integration_id)
        return integration_to_domain(row) if row is not None else None

    async def get_by_key_hash(self, key_hash: str) -> Integration | None:
        row = await self._session.scalar(
            select(IntegrationRow).where(IntegrationRow.key_hash == key_hash)
        )
        return integration_to_domain(row) if row is not None else None

    async def save(self, integration: Integration) -> None:
        row = await self._session.get(IntegrationRow, integration.id)
        if row is None:
            raise LookupError(f"Integration {integration.id} is not persisted")
        apply_settings(row, integration)

    async def list_for_company(self, company_id: UUID) -> list[Integration]:
        rows = await self._session.scalars(
            select(IntegrationRow)
            .where(IntegrationRow.company_id == company_id)
            .order_by(IntegrationRow.created_at)
        )
        return [integration_to_domain(row) for row in rows]

    async def get_link(
        self, integration_id: UUID, ticket_id: UUID
    ) -> ExternalLink | None:
        row = await self._session.get(
            ExternalTicketLinkRow, (integration_id, ticket_id)
        )
        return link_to_domain(row) if row is not None else None

    async def find_link(
        self, integration_id: UUID, external_id: str
    ) -> ExternalLink | None:
        row = await self._session.scalar(
            select(ExternalTicketLinkRow).where(
                ExternalTicketLinkRow.integration_id == integration_id,
                ExternalTicketLinkRow.external_id == external_id,
            )
        )
        return link_to_domain(row) if row is not None else None

    async def save_link(self, link: ExternalLink) -> None:
        row = await self._session.get(
            ExternalTicketLinkRow, (link.integration_id, link.ticket_id)
        )
        if row is None:
            row = ExternalTicketLinkRow(
                integration_id=link.integration_id, ticket_id=link.ticket_id
            )
            self._session.add(row)
        row.external_id = link.external_id
        row.external_number = link.external_number
        row.external_url = link.external_url
        row.external_status = link.external_status
        row.updated_at = link.updated_at
