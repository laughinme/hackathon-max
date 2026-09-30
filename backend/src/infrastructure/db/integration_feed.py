"""PostgreSQL event feed and webhook delivery state, outside business
transactions (like the notification outbox reader).

Feed order is `seq`, allocated at INSERT. A transaction that started earlier
may commit a smaller `seq` after a reader has already moved past it; reading
only events recorded more than `COMMIT_LAG` ago closes that gap for any
transaction shorter than the lag (ours take milliseconds).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import case, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domain.integrations.entities import ExternalLink, Integration, IntegrationEvent
from infrastructure.db.integration_models import (
    ExternalTicketLinkRow,
    IntegrationEventRow,
    IntegrationRow,
)
from infrastructure.db.integrations import (
    event_to_domain,
    integration_to_domain,
    link_to_domain,
)

COMMIT_LAG = timedelta(seconds=2)
#: A claimed webhook is due again after this if the relay dies mid-round.
CLAIM_LEASE = timedelta(minutes=2)


class SqlIntegrationFeed:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        commit_lag: timedelta = COMMIT_LAG,
    ) -> None:
        self._session_factory = session_factory
        self._commit_lag = commit_lag

    def _visible(self, company_id: object, after_seq: object) -> tuple:
        return (
            IntegrationEventRow.company_id == company_id,
            IntegrationEventRow.seq > after_seq,
            IntegrationEventRow.recorded_at < func.now() - self._commit_lag,
        )

    async def claim_due_webhooks(self, now: datetime, limit: int) -> list[Integration]:
        has_events = exists().where(
            *self._visible(IntegrationRow.company_id, IntegrationRow.delivered_seq)
        )
        async with self._session_factory() as session, session.begin():
            rows = (
                await session.scalars(
                    select(IntegrationRow)
                    .where(
                        IntegrationRow.enabled.is_(True),
                        IntegrationRow.webhook_url.is_not(None),
                        or_(
                            IntegrationRow.next_attempt_at.is_(None),
                            IntegrationRow.next_attempt_at <= now,
                        ),
                        has_events,
                    )
                    .order_by(IntegrationRow.created_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True, of=IntegrationRow)
                )
            ).all()
            claimed = [integration_to_domain(row) for row in rows]
            for row in rows:
                row.next_attempt_at = now + CLAIM_LEASE
        return claimed

    async def events_after(
        self, company_id: UUID, after_seq: int, limit: int
    ) -> list[IntegrationEvent]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(IntegrationEventRow)
                .where(*self._visible(company_id, after_seq))
                .order_by(IntegrationEventRow.seq)
                .limit(limit)
            )
            return [event_to_domain(row) for row in rows]

    async def links_for(
        self, integration_id: UUID, ticket_ids: list[UUID]
    ) -> dict[UUID, ExternalLink]:
        if not ticket_ids:
            return {}
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(ExternalTicketLinkRow).where(
                    ExternalTicketLinkRow.integration_id == integration_id,
                    ExternalTicketLinkRow.ticket_id.in_(ticket_ids),
                )
            )
            return {row.ticket_id: link_to_domain(row) for row in rows}

    async def pending_count(self, company_id: UUID, after_seq: int) -> int:
        async with self._session_factory() as session:
            value = await session.scalar(
                select(func.count())
                .select_from(IntegrationEventRow)
                .where(
                    IntegrationEventRow.company_id == company_id,
                    IntegrationEventRow.seq > after_seq,
                )
            )
            return int(value or 0)

    async def record_progress(
        self, integration_id: UUID, delivered_seq: int, now: datetime
    ) -> None:
        await self._update(
            integration_id,
            last_success_at=case(
                (IntegrationRow.delivered_seq != delivered_seq, now),
                else_=IntegrationRow.last_success_at,
            ),
            delivered_seq=delivered_seq,
            failures=0,
            next_attempt_at=None,
            last_error=None,
        )

    async def record_failure(
        self, integration_id: UUID, error: str, retry_at: datetime
    ) -> None:
        await self._update(
            integration_id,
            failures=IntegrationRow.failures + 1,
            last_error=error,
            next_attempt_at=retry_at,
        )

    async def _update(self, integration_id: UUID, **values: object) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                update(IntegrationRow)
                .where(IntegrationRow.id == integration_id)
                .values(**values)
            )
