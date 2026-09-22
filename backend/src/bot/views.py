"""Screens shared by several handlers: main menu and building choice."""

from __future__ import annotations

from typing import Any

from maxapi.context.base import BaseContext

from app.services import Services
from bot import home_keyboards, home_texts
from bot.screen import SCREEN_KEY, render, sender_id

DEMO_BUILDINGS = 3


async def show_main_menu(
    event: Any,
    context: BaseContext,
    services: Services,
    *,
    name: str | None,
    notification: str | None = None,
) -> None:
    """Reset the scenario (keep the screen message) and show the menu."""

    data = await context.get_data()
    await context.set_state(None)
    await context.set_data({k: v for k, v in data.items() if k == SCREEN_KEY})
    user_id = sender_id(event)
    identity = await services.identify.execute(user_id)
    await render(
        event,
        context,
        home_texts.greeting(name, identity),
        home_keyboards.main_menu(identity, services.config.demo_mode),
        notification=notification,
    )


async def show_building_choice(
    event: Any, context: BaseContext, services: Services, *, pending_problem: bool
) -> None:
    options = await services.list_demo_buildings.execute(DEMO_BUILDINGS)
    await render(
        event,
        context,
        home_texts.choose_building(pending_problem),
        home_keyboards.buildings(options),
    )
