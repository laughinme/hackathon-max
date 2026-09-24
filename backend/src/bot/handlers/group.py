"""House chat: bind to a building, notice complaints, file them, "me too"."""

from __future__ import annotations

import logging
from uuid import UUID

from maxapi import Router
from maxapi.enums.message_link_type import MessageLinkType
from maxapi.enums.upload_type import UploadType
from maxapi.filters.command import Command
from maxapi.types.input_media import InputMediaBuffer
from maxapi.types.message import NewMessageLink
from maxapi.types.updates.bot_added import BotAdded
from maxapi.types.updates.bot_removed import BotRemoved
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from app.services import Services
from application.chats.bind_chat import ChatBinding
from application.chats.file_from_chat import FileFromChatCommand
from application.chats.spot_complaint import KnownProblem
from bot import callbacks, extras_texts, group_keyboards, group_texts, media
from bot.scopes import GroupScope
from bot.screen import user_message_text
from domain.errors import DomainError
from domain.tickets.exceptions import TicketClosedError

logger = logging.getLogger(__name__)

router = Router(router_id="group")
router.filter(GroupScope())

EMERGENCY_ANSWERS = {"e": True, "n": False, "a": None}


@router.bot_added()
async def on_bot_added(event: BotAdded, services: Services) -> None:
    await services.register_chat.execute(event.chat_id, event.user.user_id)
    await _post_binding_prompt(event, event.chat_id, services)


@router.bot_removed()
async def on_bot_removed(event: BotRemoved, services: Services) -> None:
    await services.leave_chat.execute(event.chat_id)


@router.message_created(Command("start"))
async def on_start(event: MessageCreated, services: Services) -> None:
    chat_id = event.message.recipient.chat_id
    if chat_id is not None:
        await _post_binding_prompt(event, chat_id, services)


@router.message_created()
async def on_message(event: MessageCreated, services: Services) -> None:
    message = event.message
    chat_id = message.recipient.chat_id
    if chat_id is None or message.sender is None or message.body is None:
        return
    text = user_message_text(event)
    if not text:
        return
    spotted = await services.spot_complaint.execute(
        chat_id,
        message.sender.user_id,
        message.body.mid,
        text,
        tuple(media.message_photos(event)),
    )
    if spotted is None:
        return

    reply = NewMessageLink(type=MessageLinkType.REPLY, mid=message.body.mid)
    bot = event._ensure_bot()  # noqa: SLF001
    if isinstance(spotted, KnownProblem):
        await bot.send_message(
            chat_id=chat_id,
            text=group_texts.known_problem(spotted.ticket),
            attachments=[
                group_keyboards.card(spotted.ticket, services.config.bot_link)
            ],
            link=reply,
        )
        return
    hint = spotted.hint
    await bot.send_message(
        chat_id=chat_id,
        text=group_texts.hint(
            hint.category_code, spotted.deadlines, hint.needs_emergency_confirmation
        ),
        attachments=[group_keyboards.hint(hint.id, hint.needs_emergency_confirmation)],
        link=reply,
    )


@router.message_callback(callbacks.has_action(callbacks.GROUP_BUILDING))
async def on_building(event: MessageCallback, services: Services) -> None:
    _, code = callbacks.unpack(event.callback.payload)
    chat_id = event.message.recipient.chat_id if event.message else None
    if chat_id is None or not code:
        await event.ack()
        return
    try:
        binding = await services.bind_chat.execute(
            chat_id, code, event.callback.user.user_id
        )
    except DomainError:
        await event.ack(notification="Такого дома нет")
        return
    link = f"{services.config.bot_link}?start=h_{binding.building.code}"
    await event.edit(
        text=group_texts.bound(binding.building, link),
        attachments=[group_keyboards.house_tools()],
        notification="Чат привязан к дому",
    )


@router.message_callback(callbacks.has_action(callbacks.GROUP_FILE))
async def on_file(event: MessageCallback, services: Services) -> None:
    _, argument = callbacks.unpack(event.callback.payload)
    raw_id, _, answer = (argument or "").partition(":")
    if event.message is None or event.message.body is None:
        await event.ack()
        return
    try:
        ticket = await services.file_from_chat.execute(
            FileFromChatCommand(
                hint_id=UUID(raw_id),
                user_id=event.callback.user.user_id,
                card_mid=event.message.body.mid,
                is_emergency=EMERGENCY_ANSWERS.get(answer),
            )
        )
    except (ValueError, DomainError) as exc:
        logger.info("Cannot file from chat: %s", exc)
        await event.ack(notification="Не получилось оформить, напишите боту в личку")
        return
    await event.edit(
        text=group_texts.card(ticket),
        attachments=[group_keyboards.card(ticket, services.config.bot_link)],
        notification=f"Заявка № {ticket.number} отправлена в УО",
    )


@router.message_callback(callbacks.has_action(callbacks.GROUP_DROP))
async def on_drop(event: MessageCallback) -> None:
    await event.ack(notification="Хорошо, не оформляю")
    try:
        await event.delete()
    except Exception:  # noqa: BLE001 - the hint may already be gone
        logger.info("Hint message already removed")


@router.message_callback(callbacks.has_action(callbacks.GROUP_SUPPORT))
async def on_support(event: MessageCallback, services: Services) -> None:
    _, raw_id = callbacks.unpack(event.callback.payload)
    try:
        result = await services.support_ticket.execute(
            UUID(raw_id or ""), event.callback.user.user_id
        )
    except TicketClosedError:
        await event.ack(notification="Заявка уже закрыта")
        return
    except (ValueError, DomainError):
        await event.ack(notification="Заявка не найдена")
        return

    ticket = result.ticket
    if not result.counted:
        mine = ticket.reporter_id == event.callback.user.user_id
        await event.ack(
            notification="Это ваша заявка" if mine else "Вы уже поддержали эту заявку"
        )
        return
    body = event.message.body if event.message else None
    is_card = body is not None and body.mid == ticket.chat_card_mid
    await event.edit(
        text=group_texts.card(ticket) if is_card else group_texts.known_problem(ticket),
        attachments=[group_keyboards.card(ticket, services.config.bot_link)],
        notification=f"Учтено! Поддержали: {ticket.supporters_count}",
    )


@router.message_callback(callbacks.is_action(callbacks.GROUP_PULSE))
async def on_pulse(event: MessageCallback, services: Services) -> None:
    binding = await _binding(event, services)
    if binding is None:
        await event.ack(notification="Сначала выберите дом этого чата")
        return
    pulse = await services.building_pulse.execute(binding.building.id)
    await event.ack()
    await event._ensure_bot().send_message(  # noqa: SLF001
        chat_id=binding.chat.chat_id,
        text=extras_texts.pulse(binding.building.address, pulse),
    )


@router.message_callback(callbacks.is_action(callbacks.GROUP_LEAFLET))
async def on_leaflet(event: MessageCallback, services: Services) -> None:
    binding = await _binding(event, services)
    if binding is None:
        await event.ack(notification="Сначала выберите дом этого чата")
        return
    document = await services.leaflet.execute(binding.building.id)
    await event.ack(notification="Готовлю листовку")
    await event._ensure_bot().send_message(  # noqa: SLF001
        chat_id=binding.chat.chat_id,
        text=extras_texts.leaflet_caption(binding.building.address),
        attachments=[
            InputMediaBuffer(
                document.content, filename=document.filename, type=UploadType.FILE
            )
        ],
    )


@router.message_callback(callbacks.is_action(callbacks.GROUP_GUIDE))
async def on_guide(event: MessageCallback) -> None:
    await event.ack()
    chat_id = event.message.recipient.chat_id if event.message else None
    if chat_id is not None:
        await event._ensure_bot().send_message(  # noqa: SLF001
            chat_id=chat_id, text=extras_texts.guide()
        )


async def _binding(event: MessageCallback, services: Services) -> ChatBinding | None:
    chat_id = event.message.recipient.chat_id if event.message else None
    return await services.chat_binding.execute(chat_id) if chat_id else None


async def _post_binding_prompt(event: object, chat_id: int, services: Services) -> None:
    bot = event._ensure_bot()  # type: ignore[attr-defined]  # noqa: SLF001
    binding = await services.chat_binding.execute(chat_id)
    if binding is not None:
        link = f"{services.config.bot_link}?start=h_{binding.building.code}"
        await bot.send_message(
            chat_id=chat_id,
            text=group_texts.bound(binding.building, link),
            attachments=[group_keyboards.house_tools()],
        )
        return
    buildings = await services.list_demo_buildings.execute()
    await bot.send_message(
        chat_id=chat_id,
        text=group_texts.welcome(),
        attachments=[group_keyboards.buildings(buildings)],
    )
