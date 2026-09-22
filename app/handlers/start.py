"""Входные точки: первый старт, команда /start и возврат в главное меню."""

from __future__ import annotations

from maxapi import Router
from maxapi.context import MemoryContext
from maxapi.filters.command import Command
from maxapi.types.updates import BotStarted, MessageCallback, MessageCreated

from app import callbacks, keyboards, texts
from app.screen import SCREEN_KEY, render

router = Router(router_id="start")


@router.bot_started()
async def on_bot_started(
    event: BotStarted, context: MemoryContext
) -> None:
    """Первый запуск бота пользователем."""

    await _show_main_menu(event, context, name=event.user.first_name)


@router.message_created(Command("start"))
@router.message_created(Command("menu"))
async def on_start_command(
    event: MessageCreated, context: MemoryContext
) -> None:
    """Команды /start и /menu возвращают в главное меню."""

    sender = event.message.sender
    await _show_main_menu(
        event, context, name=sender.first_name if sender else None
    )


@router.message_callback(callbacks.is_action(callbacks.MENU))
async def on_menu(event: MessageCallback, context: MemoryContext) -> None:
    """Кнопка «Главное меню»."""

    await _show_main_menu(event, context, name=event.callback.user.first_name)


async def _show_main_menu(event, context: MemoryContext, name: str | None):
    """Сбрасывает сценарий и показывает главное меню."""

    data = await context.get_data()
    await context.set_state(None)
    await context.set_data(
        {k: v for k, v in data.items() if k == SCREEN_KEY}
    )
    await render(
        event, context, texts.greeting(name), keyboards.main_menu()
    )
