"""The connection itself: who am I, where to push events, the event feed."""

from __future__ import annotations

from fastapi import APIRouter, Query

from api.integration.deps import IntegrationDep, ServicesDep
from api.integration.schemas import (
    EventOut,
    EventPageOut,
    IntegrationOut,
    PingOut,
    StatusMapIn,
    WebhookIn,
    WebhookOut,
)
from application.integrations.configure_webhook import WebhookCommand

router = APIRouter()


@router.get(
    "/me",
    response_model=IntegrationOut,
    tags=["connection"],
    summary="Проверить ключ и состояние доставки вебхуков",
)
async def me(integration: IntegrationDep, services: ServicesDep) -> IntegrationOut:
    return IntegrationOut.from_view(
        await services.integrations.describe.execute(integration)
    )


@router.put(
    "/webhook",
    response_model=WebhookOut,
    tags=["connection"],
    summary="Куда присылать события и какие; возвращает секрет подписи",
)
async def configure_webhook(
    body: WebhookIn, integration: IntegrationDep, services: ServicesDep
) -> WebhookOut:
    settings = await services.integrations.configure_webhook.execute(
        WebhookCommand(
            integration_id=integration.id,
            url=body.url,
            event_types=frozenset(body.event_types),
            rotate_secret=body.rotate_secret,
        )
    )
    return WebhookOut(
        url=settings.url, event_types=list(settings.event_types), secret=settings.secret
    )


@router.post(
    "/webhook/test",
    response_model=PingOut,
    tags=["connection"],
    summary="Отправить подписанное тестовое событие ping прямо сейчас",
)
async def test_webhook(integration: IntegrationDep, services: ServicesDep) -> PingOut:
    result = await services.integrations.ping_webhook.execute(integration)
    return PingOut(
        ok=result.ok,
        status_code=result.status_code,
        error=result.error,
        answer=result.answer,
    )


@router.put(
    "/status-map",
    response_model=IntegrationOut,
    tags=["connection"],
    summary="Таблица соответствия ваших статусов нашим",
)
async def set_status_map(
    body: StatusMapIn, integration: IntegrationDep, services: ServicesDep
) -> IntegrationOut:
    view = await services.integrations.set_status_map.execute(integration.id, body.map)
    return IntegrationOut.from_view(view)


@router.get(
    "/events",
    response_model=EventPageOut,
    tags=["events"],
    summary="Лента событий по курсору — вместо вебхука, если к вам нельзя "
    "достучаться по HTTP",
)
async def list_events(
    integration: IntegrationDep,
    services: ServicesDep,
    after: int = Query(default=0, ge=0, description="next_after прошлого ответа"),
    limit: int = Query(default=100, ge=1, le=200),
) -> EventPageOut:
    page = await services.integrations.list_events.execute(integration, after, limit)
    return EventPageOut(
        events=[EventOut.model_validate(event) for event in page.events],
        next_after=page.next_after,
        has_more=page.has_more,
    )
