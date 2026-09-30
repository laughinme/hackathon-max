"""The dispatcher connects the company's CRM from the mini-app: one button
gives an API key and the address of the integration API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from api.http.deps import IdentityDep, ServicesDep
from api.integration.app import PREFIX
from api.integration.schemas import IntegrationOut

router = APIRouter(prefix="/dispatcher/integrations", tags=["integrations"])


class ConnectIn(BaseModel):
    name: str = Field(default="CRM", max_length=100, examples=["1С:Жилищный стандарт"])


class ConnectedOut(BaseModel):
    integration: IntegrationOut
    api_key: str = Field(description="Показывается один раз: сохраните его")
    api_base_url: str
    docs_url: str


@router.get(
    "",
    response_model=list[IntegrationOut],
    summary="Подключённые системы УО и состояние доставки",
)
async def list_integrations(
    identity: IdentityDep, services: ServicesDep
) -> list[IntegrationOut]:
    views = await services.integrations.list_for_dispatcher.execute(
        identity.max_user_id
    )
    return [IntegrationOut.from_view(view) for view in views]


@router.post(
    "",
    response_model=ConnectedOut,
    status_code=201,
    summary="Подключить систему: выдать API-ключ",
)
async def connect(
    body: ConnectIn, request: Request, identity: IdentityDep, services: ServicesDep
) -> ConnectedOut:
    connected = await services.integrations.connect.execute(
        identity.max_user_id, body.name
    )
    base = str(request.base_url).rstrip("/") + PREFIX
    return ConnectedOut(
        integration=IntegrationOut.from_view(connected.integration),
        api_key=connected.api_key,
        api_base_url=base,
        docs_url=f"{base}/docs",
    )


@router.delete(
    "/{integration_id}",
    status_code=204,
    summary="Отключить систему: ключ перестаёт работать сразу",
)
async def revoke(
    integration_id: UUID, identity: IdentityDep, services: ServicesDep
) -> Response:
    await services.integrations.revoke.execute(identity.max_user_id, integration_id)
    return Response(status_code=204)
