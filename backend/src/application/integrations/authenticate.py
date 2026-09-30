"""Who is calling the integration API: the connection behind an API key."""

from __future__ import annotations

from application.integrations.credentials import KEY_PREFIX, hash_api_key
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.integrations.entities import Integration
from domain.integrations.exceptions import InvalidApiKeyError


class AuthenticateIntegration:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, api_key: str | None) -> Integration:
        key = (api_key or "").strip()
        if not key.startswith(KEY_PREFIX):
            raise InvalidApiKeyError()
        async with self._uow_factory() as uow:
            integration = await uow.integrations.get_by_key_hash(hash_api_key(key))
        if integration is None or not integration.enabled:
            raise InvalidApiKeyError()
        return integration
