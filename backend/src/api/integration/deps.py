"""The connected system behind the request's API key."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.services import Services
from domain.integrations.entities import Integration

bearer = HTTPBearer(auto_error=False, description="Authorization: Bearer dmv_…")
api_key_header = APIKeyHeader(
    name="X-Api-Key", auto_error=False, description="Или заголовок X-Api-Key: dmv_…"
)


def get_services(request: Request) -> Services:
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


async def current_integration(
    services: ServicesDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)],
    api_key: Annotated[str | None, Security(api_key_header)],
) -> Integration:
    key = credentials.credentials if credentials is not None else api_key
    return await services.integrations.authenticate.execute(key)


IntegrationDep = Annotated[Integration, Depends(current_integration)]
