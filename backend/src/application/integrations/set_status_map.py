"""The system names its own status codes: {"WORKING": "in_progress", ...}.

After that it sends and receives its codes as they are, and nobody on its
side has to learn ours.
"""

from __future__ import annotations

from uuid import UUID

from application.integrations.dto import IntegrationView, to_integration_view
from application.integrations.queries import pending_events
from application.ports.integrations import IntegrationFeed
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.integrations.exceptions import (
    IntegrationNotFoundError,
    UnknownExternalStatusError,
)
from domain.tickets.enums import TicketStatus

MAX_ENTRIES = 50


class SetStatusMap:
    def __init__(self, uow_factory: UnitOfWorkFactory, feed: IntegrationFeed) -> None:
        self._uow_factory = uow_factory
        self._feed = feed

    async def execute(
        self, integration_id: UUID, mapping: dict[str, str]
    ) -> IntegrationView:
        status_map: dict[str, TicketStatus] = {}
        for code, ours in list(mapping.items())[:MAX_ENTRIES]:
            try:
                status_map[code.strip()] = TicketStatus(ours.strip().lower())
            except ValueError:
                raise UnknownExternalStatusError(ours) from None

        async with self._uow_factory() as uow:
            integration = await uow.integrations.get(integration_id)
            if integration is None:
                raise IntegrationNotFoundError()
            integration.status_map = {k: v for k, v in status_map.items() if k}
            await uow.integrations.save(integration)
            await uow.commit()

        return to_integration_view(
            integration, await pending_events(self._feed, integration)
        )
