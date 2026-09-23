"""Resident and dispatcher ticket endpoints for the mini-app."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from api.http.deps import IdentityDep, ServicesDep
from api.http.v1.schemas.tickets import (
    ConfirmationIn,
    StatusChangeIn,
    TicketOut,
    Viewer,
)
from app.services import Services
from application.housing.identity import Identity
from application.tickets.change_status import ChangeStatusCommand
from application.tickets.dto import TicketView
from domain.tickets.enums import ActorRole, TicketStatus

router = APIRouter(tags=["tickets"])


def _out(
    view: TicketView,
    identity: Identity,
    services: Services,
    role: ActorRole | None = None,
) -> TicketOut:
    """`role` picks `available_statuses`; reporter-only flags (confirm,
    complaint, demo deadline) follow the viewer, even if they also dispatch."""

    if role is None:
        dispatcher = identity.dispatcher
        is_dispatcher = (
            dispatcher is not None and dispatcher.company_id == view.company_id
        )
        role = ActorRole.DISPATCHER if is_dispatcher else ActorRole.RESIDENT
    viewer = Viewer(
        user_id=identity.max_user_id, role=role, demo_mode=services.config.demo_mode
    )
    return TicketOut.from_view(view, viewer)


@router.get("/tickets", response_model=list[TicketOut], summary="My tickets")
async def list_my_tickets(
    identity: IdentityDep, services: ServicesDep
) -> list[TicketOut]:
    views = await services.list_tickets.execute(identity.max_user_id)
    return [_out(view, identity, services, ActorRole.RESIDENT) for view in views]


@router.get(
    "/dispatcher/queue",
    response_model=list[TicketOut],
    summary="Dispatcher queue: open tickets first, by deadline",
)
async def dispatcher_queue(
    identity: IdentityDep,
    services: ServicesDep,
    include_closed: bool = Query(default=False),
) -> list[TicketOut]:
    views = await services.list_queue.execute(
        identity.max_user_id, open_only=not include_closed
    )
    return [_out(view, identity, services, ActorRole.DISPATCHER) for view in views]


@router.get("/tickets/{ticket_id}", response_model=TicketOut, summary="Ticket card")
async def get_ticket(
    ticket_id: UUID, identity: IdentityDep, services: ServicesDep
) -> TicketOut:
    view = await services.get_ticket.execute(ticket_id, identity.max_user_id)
    return _out(view, identity, services)


@router.post(
    "/tickets/{ticket_id}/status",
    response_model=TicketOut,
    summary="Dispatcher moves the ticket; the resident gets a notification",
)
async def change_status(
    ticket_id: UUID, body: StatusChangeIn, identity: IdentityDep, services: ServicesDep
) -> TicketOut:
    view = await services.change_status.execute(
        ChangeStatusCommand(
            ticket_id=ticket_id,
            target=TicketStatus(body.status),
            actor_role=ActorRole.DISPATCHER,
            actor_id=identity.max_user_id,
            comment=body.comment,
        )
    )
    return _out(view, identity, services, ActorRole.DISPATCHER)


@router.post(
    "/tickets/{ticket_id}/confirmation",
    response_model=TicketOut,
    summary="Reporter confirms the fix or reopens the ticket",
)
async def confirm(
    ticket_id: UUID, body: ConfirmationIn, identity: IdentityDep, services: ServicesDep
) -> TicketOut:
    target = TicketStatus.CONFIRMED if body.resolved else TicketStatus.IN_PROGRESS
    view = await services.change_status.execute(
        ChangeStatusCommand(
            ticket_id=ticket_id,
            target=target,
            actor_role=ActorRole.RESIDENT,
            actor_id=identity.max_user_id,
            comment=body.comment,
        )
    )
    return _out(view, identity, services)


@router.post(
    "/tickets/{ticket_id}/escalation",
    response_model=TicketOut,
    status_code=202,
    summary="Reporter asks for a complaint to the housing inspection; "
    "the bot sends the PDF to the reporter's chat",
)
async def escalate(
    ticket_id: UUID, identity: IdentityDep, services: ServicesDep
) -> TicketOut:
    view = await services.escalate.execute(ticket_id, identity.max_user_id)
    return _out(view, identity, services)


@router.post(
    "/tickets/{ticket_id}/demo/expire-deadline",
    response_model=TicketOut,
    summary="DEMO_MODE only: move the reporter's deadline into the past, so the "
    "overdue notice and the complaint can be checked without waiting",
)
async def demo_expire_deadline(
    ticket_id: UUID, identity: IdentityDep, services: ServicesDep
) -> TicketOut:
    view = await services.demo_expire_deadline.execute(ticket_id, identity.max_user_id)
    return _out(view, identity, services)
