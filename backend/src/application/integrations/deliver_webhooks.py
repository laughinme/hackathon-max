"""Relay the event feed to each connected system's webhook, in order.

Each connection has a cursor in its company's feed. Events go one by one:
a system sees a ticket's changes in the order they happened. While the
system is down its events wait (retries back off, nothing is dropped); an
event it rejects as invalid (4xx) is skipped, so one bad event never blocks
the rest — the system can still read it from the feed.

A 2xx answer may carry the system's record: `{"external_id": "58391",
"external_number": "АДС-58391"}` links the ticket without a second call.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from application.integrations.dto import ExternalRecord
from application.integrations.link_ticket import upsert_link
from application.integrations.payload import envelope
from application.ports.clock import Clock
from application.ports.integrations import IntegrationFeed, WebhookSender
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.errors import DomainError
from domain.integrations.entities import ExternalLink, Integration, IntegrationEvent

logger = logging.getLogger(__name__)

BACKOFF = (
    timedelta(seconds=10),
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=30),
)
#: Answers worth retrying; any other 4xx means "this event is invalid for us".
RETRYABLE_4XX = frozenset({408, 409, 425, 429})
EVENTS_PER_ROUND = 20
WEBHOOKS_PER_ROUND = 10


def is_success(status_code: int) -> bool:
    return 200 <= status_code < 300


def is_retryable(status_code: int) -> bool:
    """Server errors, throttling and redirects (not followed: the URL is
    probably outdated) are retried until the system fixes them."""

    return (
        status_code >= 500 or 300 <= status_code < 400 or status_code in RETRYABLE_4XX
    )


def record_from_answer(body: dict[str, Any] | None) -> ExternalRecord | None:
    if not body:
        return None
    external_id = body.get("external_id")
    if external_id is None or str(external_id).strip() == "":
        return None
    return ExternalRecord(
        id=str(external_id).strip(),
        number=_text(body.get("external_number")),
        url=_text(body.get("external_url")),
        status=_text(body.get("external_status")),
    )


def _text(value: Any) -> str | None:
    return str(value).strip() or None if value is not None else None


class DeliverWebhooks:
    def __init__(
        self,
        feed: IntegrationFeed,
        sender: WebhookSender,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._feed = feed
        self._sender = sender
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self) -> int:
        """One round over due webhooks; returns how many events were handled."""

        handled = 0
        now = self._clock.now()
        for integration in await self._feed.claim_due_webhooks(now, WEBHOOKS_PER_ROUND):
            handled += await self._drain(integration)
        return handled

    async def _drain(self, integration: Integration) -> int:
        events = await self._feed.events_after(
            integration.company_id, integration.delivered_seq, EVENTS_PER_ROUND
        )
        links = await self._feed.links_for(
            integration.id, list({event.ticket_id for event in events})
        )
        position, handled = integration.delivered_seq, 0
        error: str | None = None
        for event in events:
            if integration.wants(event):
                error = await self._deliver(
                    integration, event, links.get(event.ticket_id)
                )
                if error is not None:
                    break
            assert event.seq is not None
            position, handled = event.seq, handled + 1

        now = self._clock.now()
        moved = position != integration.delivered_seq
        if moved or error is None:
            # Clears the lease and, once something went through, the failures.
            await self._feed.record_progress(integration.id, position, now)
        if error is not None:
            attempt = 1 if moved else integration.failures + 1
            delay = BACKOFF[min(attempt, len(BACKOFF)) - 1]
            logger.warning(
                "Webhook of integration %s failed (attempt %s): %s",
                integration.id,
                attempt,
                error,
            )
            await self._feed.record_failure(integration.id, error, now + delay)
        return handled

    async def _deliver(
        self,
        integration: Integration,
        event: IntegrationEvent,
        link: ExternalLink | None,
    ) -> str | None:
        """None when the event is done with (delivered or rejected for good),
        otherwise the error to retry on."""

        assert integration.webhook_url is not None
        assert integration.webhook_secret is not None
        try:
            response = await self._sender.send(
                integration.webhook_url,
                integration.webhook_secret,
                envelope(event, integration, link),
            )
        except Exception as exc:  # noqa: BLE001 - network errors are retried
            return f"{type(exc).__name__}: {exc}"[:500]

        if is_retryable(response.status_code):
            return f"HTTP {response.status_code} for event {event.id}"
        if not is_success(response.status_code):
            logger.warning(
                "Integration %s rejected event %s with HTTP %s; skipped",
                integration.id,
                event.id,
                response.status_code,
            )
            return None
        record = record_from_answer(response.body)
        if record is not None:
            await self._link(integration, event, record)
        return None

    async def _link(
        self, integration: Integration, event: IntegrationEvent, record: ExternalRecord
    ) -> None:
        try:
            async with self._uow_factory() as uow:
                await upsert_link(
                    uow, integration.id, event.ticket_id, record, self._clock.now()
                )
                await uow.commit()
        except DomainError as exc:
            logger.warning("Link from webhook answer ignored: %s", exc.message)
