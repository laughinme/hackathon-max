"""A dispatcher connects the company's CRM: a new integration and its API key."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from application.integrations.credentials import (
    hash_api_key,
    new_api_key,
    visible_prefix,
)
from application.integrations.dto import IntegrationView, to_integration_view
from application.ports.clock import Clock
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.housing.exceptions import NotADispatcherError
from domain.integrations.entities import Integration

DEFAULT_NAME = "CRM"
MAX_NAME_LENGTH = 100


@dataclass(frozen=True, slots=True)
class ConnectedIntegration:
    integration: IntegrationView
    #: Shown once: only its hash is stored.
    api_key: str


class ConnectIntegration:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, dispatcher_id: int, name: str) -> ConnectedIntegration:
        now = self._clock.now()
        key = new_api_key()
        async with self._uow_factory() as uow:
            dispatcher = await uow.housing.get_dispatcher(dispatcher_id)
            if dispatcher is None:
                raise NotADispatcherError()
            integration = Integration(
                id=uuid4(),
                company_id=dispatcher.company_id,
                name=name.strip()[:MAX_NAME_LENGTH] or DEFAULT_NAME,
                key_prefix=visible_prefix(key),
                key_hash=hash_api_key(key),
                created_at=now,
                # A webhook starts from the next change; history is in the feed.
                delivered_seq=await uow.integration_events.latest_seq(
                    dispatcher.company_id
                ),
            )
            await uow.integrations.add(integration)
            await uow.commit()
        return ConnectedIntegration(to_integration_view(integration, 0), key)
