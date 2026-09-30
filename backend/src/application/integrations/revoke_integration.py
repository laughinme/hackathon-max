"""A dispatcher disconnects a system: its key stops working at once."""

from __future__ import annotations

from uuid import UUID

from application.ports.unit_of_work import UnitOfWorkFactory
from domain.housing.exceptions import NotADispatcherError
from domain.integrations.exceptions import IntegrationNotFoundError


class RevokeIntegration:
    """The key stops working at once; links and history stay."""

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, dispatcher_id: int, integration_id: UUID) -> None:
        async with self._uow_factory() as uow:
            dispatcher = await uow.housing.get_dispatcher(dispatcher_id)
            if dispatcher is None:
                raise NotADispatcherError()
            integration = await uow.integrations.get(integration_id)
            if integration is None or integration.company_id != dispatcher.company_id:
                raise IntegrationNotFoundError()
            integration.enabled = False
            await uow.integrations.save(integration)
            await uow.commit()
