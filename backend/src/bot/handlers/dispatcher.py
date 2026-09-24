"""Dispatcher side in the chat: queue, ticket card, status change with comment.

The mini-app is the main dispatcher UI; this keeps the scenario checkable in
MAX even if the mini-app is not attached to the bot yet.
"""

from __future__ import annotations

from uuid import UUID

from maxapi import Router
from maxapi.context.base import BaseContext
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from app.services import Services
from application.errors import TicketNotFoundError
from application.tickets.change_status import ChangeStatusCommand
from bot import callbacks, dispatcher_keyboards, dispatcher_texts, keyboards, media
from bot.presenters import STATUS_LABELS
from bot.scopes import DialogScope
from bot.screen import render, sender_id, user_message_text
from bot.states import DispatcherFlow
from domain.errors import DomainError
from domain.housing.exceptions import NotADispatcherError
from domain.tickets.enums import ActorRole, TicketStatus

router = Router(router_id="dispatcher")
router.filter(DialogScope())

PENDING_TICKET = "dispatcher_ticket"
PENDING_STATUS = "dispatcher_status"


@router.message_callback(callbacks.is_action(callbacks.QUEUE))
async def on_queue(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    await context.set_state(None)
    user_id = sender_id(event)
    identity = await services.identify.execute(user_id)
    if identity.dispatcher is None:
        await render(
            event, context, dispatcher_texts.not_a_dispatcher(), keyboards.menu_only()
        )
        return
    tickets = await services.list_queue.execute(user_id)
    await render(
        event,
        context,
        dispatcher_texts.queue(identity.dispatcher.company_name, tickets),
        dispatcher_keyboards.queue(tickets),
    )


@router.message_callback(callbacks.has_action(callbacks.QUEUE_ITEM))
async def on_queue_item(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    await context.set_state(None)
    _, raw_id = callbacks.unpack(event.callback.payload)
    await show_card(event, context, services, UUID(raw_id or ""))


@router.message_callback(callbacks.has_action(callbacks.QUEUE_SET))
async def on_status_chosen(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    _, argument = callbacks.unpack(event.callback.payload)
    raw_id, _, status = (argument or "").partition(":")
    await context.update_data(**{PENDING_TICKET: raw_id, PENDING_STATUS: status})
    await context.set_state(DispatcherFlow.commenting)
    await render(
        event,
        context,
        dispatcher_texts.ask_comment(STATUS_LABELS[TicketStatus(status)]),
        dispatcher_keyboards.comment_prompt(UUID(raw_id)),
    )


@router.message_callback(
    DispatcherFlow.commenting, callbacks.is_action(callbacks.QUEUE_SKIP_COMMENT)
)
async def on_skip_comment(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    await apply_status(event, context, services, comment=None)


@router.message_created(DispatcherFlow.commenting)
async def on_comment(
    event: MessageCreated, context: BaseContext, services: Services
) -> None:
    comment = user_message_text(event)
    if comment:
        await apply_status(event, context, services, comment=comment)


async def apply_status(
    event: MessageCallback | MessageCreated,
    context: BaseContext,
    services: Services,
    *,
    comment: str | None,
) -> None:
    data = await context.get_data()
    await context.set_state(None)
    ticket_id = UUID(data[PENDING_TICKET])
    user_id = sender_id(event)
    notification = "Статус изменён, житель получит уведомление"
    try:
        await services.change_status.execute(
            ChangeStatusCommand(
                ticket_id=ticket_id,
                target=TicketStatus(data[PENDING_STATUS]),
                actor_role=ActorRole.DISPATCHER,
                actor_id=user_id,
                comment=comment,
            )
        )
    except DomainError:
        notification = "Статус уже изменился, обновил карточку"
    await show_card(event, context, services, ticket_id, notification=notification)


async def show_card(
    event: MessageCallback | MessageCreated,
    context: BaseContext,
    services: Services,
    ticket_id: UUID,
    *,
    notification: str | None = None,
) -> None:
    user_id = sender_id(event)
    try:
        ticket = await services.get_ticket.execute(ticket_id, user_id)
    except (TicketNotFoundError, NotADispatcherError):
        await render(
            event, context, dispatcher_texts.not_a_dispatcher(), keyboards.menu_only()
        )
        return
    await render(
        event,
        context,
        dispatcher_texts.card(ticket),
        dispatcher_keyboards.card(ticket),
        notification=notification,
        media=media.photo_attachments(ticket.photos),
    )
