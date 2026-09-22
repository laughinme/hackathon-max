""" "My tickets": list and ticket card."""

from __future__ import annotations

from uuid import UUID

from maxapi import Router
from maxapi.context import MemoryContext
from maxapi.types.updates.message_callback import MessageCallback

from app.services import Services
from application.errors import TicketNotFoundError
from bot import callbacks, keyboards, texts
from bot.screen import render

router = Router(router_id="my_requests")


@router.message_callback(callbacks.is_action(callbacks.MY_LIST))
async def on_my_requests(
    event: MessageCallback, context: MemoryContext, services: Services
) -> None:
    _, user_id = event.get_ids()
    tickets = await services.list_tickets.execute(user_id)
    text = texts.requests_list(len(tickets)) if tickets else texts.empty_requests()
    await render(event, context, text, keyboards.requests_list(tickets))


@router.message_callback(callbacks.has_action(callbacks.MY_ITEM))
async def on_request_card(
    event: MessageCallback, context: MemoryContext, services: Services
) -> None:
    _, user_id = event.get_ids()
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

    await render(event, context, texts.request_card(ticket), keyboards.request_card())
