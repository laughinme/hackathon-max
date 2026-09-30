"""Tickets for a connected system: read, link to its records, move status."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from api.integration.deps import IntegrationDep, ServicesDep
from api.integration.schemas import (
    ExternalIn,
    StatusIn,
    StatusResultOut,
    TicketOut,
    TicketPageOut,
)
from application.integrations.apply_external_status import ExternalStatusCommand
from application.integrations.dto import ExternalRecord, LinkedTicket
from application.integrations.link_ticket import LinkTicketCommand
from application.integrations.payload import for_integration, ticket_snapshot
from domain.integrations.entities import Integration

router = APIRouter(prefix="/tickets", tags=["tickets"])

TicketRef = Annotated[
    str,
    Path(
        description="Наш id (UUID), наш номер (2026-00042) или ваш id после "
        "связывания в виде ext:<id>",
        examples=["2026-00042", "ext:58391"],
    ),
]


def ticket_out(linked: LinkedTicket, integration: Integration) -> TicketOut:
    return TicketOut.model_validate(
        for_integration(ticket_snapshot(linked.view), integration, linked.link)
    )


def _record(body: ExternalIn) -> ExternalRecord:
    return ExternalRecord(
        id=body.id.strip(), number=body.number, url=body.url, status=body.status
    )


@router.get(
    "",
    response_model=TicketPageOut,
    summary="Все заявки УО по времени изменения — первичная загрузка и сверка",
)
async def list_tickets(
    integration: IntegrationDep,
    services: ServicesDep,
    cursor: str | None = Query(
        default=None, description="next_cursor прошлой страницы"
    ),
    limit: int = Query(default=50, ge=1, le=200),
) -> TicketPageOut:
    page = await services.integrations.list_tickets.execute(integration, cursor, limit)
    return TicketPageOut(
        tickets=[ticket_out(item, integration) for item in page.tickets],
        next_cursor=page.next_cursor,
    )


@router.get("/{ticket_ref}", response_model=TicketOut, summary="Карточка заявки")
async def get_ticket(
    ticket_ref: TicketRef, integration: IntegrationDep, services: ServicesDep
) -> TicketOut:
    linked = await services.integrations.get_ticket.execute(integration, ticket_ref)
    return ticket_out(linked, integration)


@router.put(
    "/{ticket_ref}/external",
    response_model=TicketOut,
    summary="Связать заявку с вашей записью (повтор безопасен)",
)
async def link_ticket(
    ticket_ref: TicketRef,
    body: ExternalIn,
    integration: IntegrationDep,
    services: ServicesDep,
) -> TicketOut:
    linked = await services.integrations.link_ticket.execute(
        LinkTicketCommand(integration, ticket_ref, _record(body))
    )
    return ticket_out(linked, integration)


@router.post(
    "/{ticket_ref}/status",
    response_model=StatusResultOut,
    summary="Сменить статус: житель получит уведомление в MAX",
    description="Действует по правилам диспетчера УО. Подтвердить устранение "
    "может только житель, поэтому `confirmed` недоступен. Повтор того же "
    "статуса ничего не меняет и возвращает `applied: false`.",
)
async def change_status(
    ticket_ref: TicketRef,
    body: StatusIn,
    integration: IntegrationDep,
    services: ServicesDep,
) -> StatusResultOut:
    result = await services.integrations.apply_status.execute(
        ExternalStatusCommand(
            integration=integration,
            ticket_ref=ticket_ref,
            status=body.status,
            comment=body.comment,
            record=_record(body.external) if body.external else None,
        )
    )
    return StatusResultOut(
        applied=result.applied, ticket=ticket_out(result.ticket, integration)
    )
