""" "My tickets": list and ticket card."""

from __future__ import annotations

from uuid import UUID

from maxapi import Router
from maxapi.context.base import BaseContext
from maxapi.types.updates.message_callback import MessageCallback

from app.services import Services
from application.errors import TicketNotFoundError
from application.tickets.change_status import ChangeStatusCommand
from bot import callbacks, keyboards, texts
from bot.screen import render, sender_id
from domain.errors import DomainError
from domain.tickets.enums import ActorRole, TicketStatus
from domain.tickets.exceptions import TicketNotOverdueError

router = Router(router_id="my_requests")


@router.message_callback(callbacks.is_action(callbacks.MY_LIST))
async def on_my_requests(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    user_id = sender_id(event)
    tickets = await services.list_tickets.execute(user_id)
    text = texts.requests_list(len(tickets)) if tickets else texts.empty_requests()
    await render(event, context, text, keyboards.requests_list(tickets))


@router.message_callback(callbacks.has_action(callbacks.MY_ITEM))
async def on_request_card(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    user_id = sender_id(event)
    _, raw_id = callbacks.unpack(event.callback.payload)

    try:
        ticket = await services.get_ticket.execute(UUID(raw_id or ""), user_id)
    except (ValueError, TicketNotFoundError):
        await render(
            event,
            context,
            texts.request_not_found(),
            keyboards.request_card(),
            notification="Заявка не найдена",
        )
        return

    await render(
        event, context, texts.request_card(ticket), keyboards.request_card(ticket)
    )


@router.message_callback(callbacks.has_action(callbacks.ESCALATE))
async def on_escalate(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    """Queue the complaint PDF; the relay sends it as a separate message."""

    user_id = sender_id(event)
    _, raw_id = callbacks.unpack(event.callback.payload)
    try:
        ticket = await services.escalate.execute(UUID(raw_id or ""), user_id)
    except (ValueError, TicketNotFoundError):
        await render(
            event, context, texts.request_not_found(), keyboards.request_card()
        )
        return
    except TicketNotOverdueError:
        ticket = await services.get_ticket.execute(UUID(raw_id or ""), user_id)
        await render(
            event,
            context,
            texts.request_card(ticket),
            keyboards.request_card(ticket),
            notification="Жалоба возможна только после истечения срока",
        )
        return
    await render(
        event,
        context,
        texts.request_card(ticket),
        keyboards.request_card(ticket),
        notification="Готовлю жалобу — PDF придёт следующим сообщением",
    )


@router.message_callback(callbacks.has_action(callbacks.CONFIRM_FIXED))
async def on_confirm_fixed(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    await _resident_answer(event, context, services, TicketStatus.CONFIRMED)


@router.message_callback(callbacks.has_action(callbacks.CONFIRM_REOPEN))
async def on_confirm_reopen(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    await _resident_answer(event, context, services, TicketStatus.IN_PROGRESS)


async def _resident_answer(
    event: MessageCallback,
    context: BaseContext,
    services: Services,
    target: TicketStatus,
) -> None:
    """The resident closes the loop from the "done" notification."""

    user_id = sender_id(event)
    _, raw_id = callbacks.unpack(event.callback.payload)
    ticket_id = UUID(raw_id or "")
    notification = (
        "Спасибо! Заявка закрыта"
        if target is TicketStatus.CONFIRMED
        else "Заявка возвращена в работу, УО получит сигнал"
    )
    try:
        ticket = await services.change_status.execute(
            ChangeStatusCommand(
                ticket_id=ticket_id,
                target=target,
                actor_role=ActorRole.RESIDENT,
                actor_id=user_id,
                comment=None
                if target is TicketStatus.CONFIRMED
                else "Житель: не починили",
            )
        )
    except DomainError:
        notification = "Ответ уже учтён"
        ticket = await services.get_ticket.execute(ticket_id, user_id)
    await render(
        event,
        context,
        texts.request_card(ticket),
        keyboards.request_card(ticket),
        notification=notification,
    )
