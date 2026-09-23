"""Свободный ввод вне сценария и обработка непредвиденных ошибок.

Chat-first: если житель просто написал о проблеме, не нажимая кнопок,
мы сразу начинаем сценарий обращения — это основной способ входа.
"""

from __future__ import annotations

import logging

from maxapi import Router
from maxapi.context.base import BaseContext
from maxapi.types.updates.message_created import MessageCreated

from app.services import Services
from bot import keyboards, texts
from bot.handlers.create import TURNS, analyze_and_render, reset_scenario
from bot.scopes import DialogScope
from bot.screen import render, sender_id, user_message_text
from bot.states import CreateRequest
from bot.views import show_building_choice

logger = logging.getLogger(__name__)
router = Router(router_id="fallback")
router.filter(DialogScope())

#: Слишком короткий текст не считаем описанием проблемы.
MIN_PROBLEM_LENGTH = 8


@router.message_created()
async def on_free_text(
    event: MessageCreated, context: BaseContext, services: Services
) -> None:
    """Пользователь описал проблему своими словами вне сценария."""

    text = user_message_text(event)
    if not text or text.startswith("/"):
        return

    if len(text) < MIN_PROBLEM_LENGTH:
        await render(event, context, texts.unknown_message(), keyboards.menu_only())
        return

    # Free text: no category hint, the classifier decides (DECISIONS D-005).
    await reset_scenario(context)
    await context.update_data(**{TURNS: [{"role": "user", "text": text}]})
    await context.set_state(CreateRequest.collecting)

    user_id = sender_id(event)
    identity = await services.identify.execute(user_id)
    if identity.residency is None:
        # Keep the problem text; the scenario continues once a building is chosen.
        await show_building_choice(event, context, services, pending_problem=True)
        return
    await analyze_and_render(event, context, services)
