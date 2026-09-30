"""The system tells where to send events and which ones."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from application.integrations.credentials import new_webhook_secret
from application.ports.integrations import WebhookSender
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.integrations.entities import ALL_EVENT_TYPES, IntegrationEventType
from domain.integrations.exceptions import IntegrationNotFoundError


@dataclass(frozen=True, slots=True)
class WebhookCommand:
    integration_id: UUID
    #: None switches the webhook off (the feed keeps working).
    url: str | None
    event_types: frozenset[IntegrationEventType] = ALL_EVENT_TYPES
    rotate_secret: bool = False


@dataclass(frozen=True, slots=True)
class WebhookSettings:
    url: str | None
    event_types: tuple[str, ...]
    #: The key for checking signatures; None while the webhook is off.
    secret: str | None


class ConfigureWebhook:
    def __init__(self, uow_factory: UnitOfWorkFactory, sender: WebhookSender) -> None:
        self._uow_factory = uow_factory
        self._sender = sender

    async def execute(self, command: WebhookCommand) -> WebhookSettings:
        url = command.url.strip() if command.url else None
        if url is not None:
            self._sender.check_url(url)
        async with self._uow_factory() as uow:
            integration = await uow.integrations.get(command.integration_id)
            if integration is None:
                raise IntegrationNotFoundError()
            if url is not None and integration.webhook_url is None:
                # A fresh webhook starts from the next change, not the history.
                integration.delivered_seq = await uow.integration_events.latest_seq(
                    integration.company_id
                )
                integration.failures = 0
                integration.next_attempt_at = None
                integration.last_error = None
            if url is not None and (
                command.rotate_secret or integration.webhook_secret is None
            ):
                integration.webhook_secret = new_webhook_secret()
            integration.webhook_url = url
            integration.event_types = command.event_types or ALL_EVENT_TYPES
            await uow.integrations.save(integration)
            await uow.commit()
        return WebhookSettings(
            url=integration.webhook_url,
            event_types=tuple(sorted(t.value for t in integration.event_types)),
            secret=integration.webhook_secret if integration.webhook_url else None,
        )
