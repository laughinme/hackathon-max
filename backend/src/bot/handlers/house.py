"""Resident's house tools in the dialog: pulse, responsibility guide, leaflet."""

from __future__ import annotations

from maxapi import Router
from maxapi.context.base import BaseContext
from maxapi.enums.upload_type import UploadType
from maxapi.types.input_media import InputMediaBuffer
from maxapi.types.updates.message_callback import MessageCallback

from app.services import Services
from bot import callbacks, extras_texts, home_texts, keyboards
from bot.scopes import DialogScope
from bot.screen import render, sender_id
from bot.views import show_building_choice

router = Router(router_id="house")
router.filter(DialogScope())


@router.message_callback(callbacks.is_action(callbacks.GUIDE))
async def on_guide(event: MessageCallback, context: BaseContext) -> None:
    await render(event, context, extras_texts.guide(), keyboards.menu_only())


@router.message_callback(callbacks.is_action(callbacks.PULSE))
async def on_pulse(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    identity = await services.identify.execute(sender_id(event))
    if identity.residency is None:
        await show_building_choice(event, context, services, pending_problem=False)
        return
    pulse = await services.building_pulse.execute(identity.residency.building_id)
    await render(
        event,
        context,
        extras_texts.pulse(identity.residency.address, pulse),
        keyboards.menu_only(),
    )


@router.message_callback(callbacks.is_action(callbacks.LEAFLET))
async def on_leaflet(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    user_id = sender_id(event)
    identity = await services.identify.execute(user_id)
    if identity.residency is None:
        await show_building_choice(event, context, services, pending_problem=False)
        return
    document = await services.leaflet.execute(identity.residency.building_id)
    await render(
        event,
        context,
        extras_texts.leaflet_caption(identity.residency.address),
        keyboards.menu_only(),
        notification=home_texts.LEAFLET_SENT,
    )
    await event._ensure_bot().send_message(  # noqa: SLF001
        user_id=user_id,
        attachments=[
            InputMediaBuffer(
                document.content, filename=document.filename, type=UploadType.FILE
            )
        ],
    )
