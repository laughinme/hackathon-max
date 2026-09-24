"""Entry points: first start (with a building code from a QR deep link),
/start and /menu, building choice and the demo dispatcher role."""

from __future__ import annotations

from uuid import UUID

from maxapi import Router
from maxapi.context.base import BaseContext
from maxapi.filters.command import Command
from maxapi.types.updates.bot_started import BotStarted
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from app.services import Services
from application.errors import TicketNotFoundError
from bot import callbacks, home_keyboards, home_texts, keyboards, media, texts
from bot.handlers.create import TURNS, analyze_and_render
from bot.scopes import DialogScope
from bot.screen import render, sender_id
from bot.views import show_building_choice, show_main_menu
from domain.housing.exceptions import BuildingNotFoundError

router = Router(router_id="start")
router.filter(DialogScope())

#: Deep link payload `https://max.ru/<bot>?start=h_<building code>`.
BUILDING_LINK_PREFIX = "h_"
#: `?start=t_<ticket id>` from "follow in private" on a house chat card.
TICKET_LINK_PREFIX = "t_"


@router.bot_started()
async def on_bot_started(
    event: BotStarted, context: BaseContext, services: Services
) -> None:
    payload = event.payload or ""
    if payload.startswith(TICKET_LINK_PREFIX):
        if await _show_ticket(event, context, services, payload):
            return
    if payload.startswith(BUILDING_LINK_PREFIX):
        code = payload.removeprefix(BUILDING_LINK_PREFIX)
        try:
            await services.bind_resident.execute(event.user.user_id, code)
        except BuildingNotFoundError:
            pass  # unknown code in the QR: fall back to the regular menu
    await show_main_menu(event, context, services, name=event.user.first_name)


@router.message_created(Command("start"))
@router.message_created(Command("menu"))
async def on_start_command(
    event: MessageCreated, context: BaseContext, services: Services
) -> None:
    sender = event.message.sender
    await show_main_menu(
        event, context, services, name=sender.first_name if sender else None
    )


@router.message_callback(callbacks.is_action(callbacks.MENU))
async def on_menu(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    await show_main_menu(event, context, services, name=event.callback.user.first_name)


@router.message_callback(callbacks.is_action(callbacks.CHANGE_BUILDING))
async def on_change_building(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    await show_building_choice(event, context, services, pending_problem=False)


@router.message_callback(callbacks.has_action(callbacks.BUILDING))
async def on_building_chosen(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    _, code = callbacks.unpack(event.callback.payload)
    user_id = sender_id(event)
    try:
        identity = await services.bind_resident.execute(user_id, code or "")
    except BuildingNotFoundError:
        await show_building_choice(event, context, services, pending_problem=False)
        return

    assert identity.residency is not None
    data = await context.get_data()
    if data.get(TURNS):  # a problem was typed before the building was known
        await analyze_and_render(event, context, services)
        return
    await show_main_menu(
        event,
        context,
        services,
        name=event.callback.user.first_name,
        notification=home_texts.building_bound(identity.residency.address),
    )


@router.message_callback(callbacks.is_action(callbacks.DEMO_DISPATCHER))
async def on_demo_dispatcher(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    if not services.config.demo_mode:
        await show_main_menu(event, context, services, name=None)
        return
    user_id = sender_id(event)
    identity = await services.become_demo_dispatcher.execute(user_id)
    assert identity.dispatcher is not None
    await render(
        event,
        context,
        home_texts.demo_dispatcher_enabled(identity.dispatcher.company_name),
        home_keyboards.main_menu(identity, services.config.demo_mode),
    )


async def _show_ticket(
    event: BotStarted, context: BaseContext, services: Services, payload: str
) -> bool:
    """Open a ticket from its house chat card; the dialog now exists, so the
    person will get the status updates in private."""

    try:
        ticket_id = UUID(payload.removeprefix(TICKET_LINK_PREFIX))
        ticket = await services.get_ticket.execute(ticket_id, event.user.user_id)
    except (ValueError, TicketNotFoundError):
        return False
    await render(
        event,
        context,
        texts.request_card(ticket),
        keyboards.request_card(ticket, demo_mode=services.config.demo_mode),
        media=media.photo_attachments(ticket.photos),
    )
    return True
