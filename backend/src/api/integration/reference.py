"""Codes for mapping and the legal deadline as a service."""

from __future__ import annotations

from fastapi import APIRouter

from api.integration.deps import IntegrationDep, ServicesDep
from api.integration.schemas import (
    CategoryOut,
    ReferenceOut,
    SlaIn,
    SlaOut,
    StatusRefOut,
)
from domain.integrations.entities import ALL_EVENT_TYPES
from domain.tickets.catalog import CATEGORIES, OTHER
from domain.tickets.enums import ActorRole, TicketStatus
from domain.tickets.state_machine import TRANSITIONS

router = APIRouter()

STATUS_TITLES: dict[TicketStatus, str] = {
    TicketStatus.REGISTERED: "Зарегистрирована",
    TicketStatus.ACKNOWLEDGED: "Принята УО",
    TicketStatus.IN_PROGRESS: "В работе",
    TicketStatus.DONE: "Выполнена, ждёт подтверждения жителя",
    TicketStatus.CONFIRMED: "Закрыта: житель подтвердил",
    TicketStatus.REJECTED: "Отклонена",
}
SETTABLE = frozenset(
    target
    for (_, target), roles in TRANSITIONS.items()
    if ActorRole.DISPATCHER in roles
)


@router.get(
    "/reference",
    response_model=ReferenceOut,
    tags=["reference"],
    summary="Коды категорий, статусов и событий — для таблиц соответствия",
)
async def reference(integration: IntegrationDep) -> ReferenceOut:
    return ReferenceOut(
        categories=[
            CategoryOut(code=category.code, title=category.title)
            for category in (*CATEGORIES, OTHER)
        ],
        statuses=[
            StatusRefOut(
                code=status,
                title=STATUS_TITLES[status],
                integration_can_set=status in SETTABLE,
            )
            for status in TicketStatus
        ],
        event_types=sorted(ALL_EVENT_TYPES),
    )


@router.post(
    "/sla/calculate",
    response_model=SlaOut,
    tags=["sla"],
    summary="Нормативный срок и основание для заявки из вашей системы",
    description="Заявку создавать не нужно: считаем срок реакции и устранения "
    "по категории и аварийности, с календарём рабочих дней и ссылкой на норму.",
)
async def calculate_sla(
    body: SlaIn, integration: IntegrationDep, services: ServicesDep
) -> SlaOut:
    quote = services.integrations.calculate_sla.execute(
        body.category_code, body.is_emergency, body.registered_at
    )
    return SlaOut(
        category=CategoryOut(code=quote.category_code, title=quote.category_title),
        is_emergency=quote.is_emergency,
        registered_at=quote.registered_at,
        react_by=quote.react_by,
        resolve_by=quote.resolve_by,
        legal_basis=quote.legal_basis,
        responsible_party=quote.responsible_party,
        responsibility_basis=quote.responsibility_basis,
        needs_verification=quote.needs_verification,
        warnings=list(quote.warnings),
    )
