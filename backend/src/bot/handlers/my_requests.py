"""Раздел «Мои обращения»: список и карточка обращения."""

from __future__ import annotations

from maxapi import Router
from maxapi.context import MemoryContext
from maxapi.types.updates import MessageCallback

from app.services import get_services
from bot import callbacks, keyboards, texts
from bot.screen import render

router = Router(router_id="my_requests")


@router.message_callback(callbacks.is_action(callbacks.MY_LIST))
async def on_my_requests(event: MessageCallback, context: MemoryContext) -> None:
    """Список обращений пользователя — по кнопке на каждое."""

    services = get_services()
    _, user_id = event.get_ids()
    requests = await services.requests.list_for_user(user_id)

    if not requests:
        await render(
            event,
            context,
            texts.empty_requests(),
            keyboards.requests_list([]),
        )
        return

    await render(
        event,
        context,
        texts.requests_list(len(requests)),
        keyboards.requests_list(requests),
    )


@router.message_callback(callbacks.has_action(callbacks.MY_ITEM))
async def on_request_card(event: MessageCallback, context: MemoryContext) -> None:
    """Карточка обращения: статус, текст и история."""

    services = get_services()
    _, user_id = event.get_ids()
    _, raw_id = callbacks.unpack(event.callback.payload)

    request = None
    if raw_id and raw_id.isdigit():
        request = await services.requests.get_for_user(int(raw_id), user_id)

    if request is None:
        await render(
            event,
            context,
            texts.request_not_found(),
            keyboards.request_card(),
            notification="Обращение не найдено",
        )
        return

    await render(
        event,
        context,
        texts.request_card(request),
        keyboards.request_card(),
    )
