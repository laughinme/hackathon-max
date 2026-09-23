"""/privacy: what is stored and deleting it on request."""

from __future__ import annotations

from maxapi import Router
from maxapi.context.base import BaseContext
from maxapi.enums.intent import Intent
from maxapi.filters.command import Command
from maxapi.types.attachments.buttons import CallbackButton
from maxapi.types.attachments.buttons.attachment_button import AttachmentButton
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from app.services import Services
from bot import callbacks, keyboards, privacy_texts
from bot.scopes import DialogScope
from bot.screen import SCREEN_KEY, render, sender_id

router = Router(router_id="privacy")
router.filter(DialogScope())


def _policy_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="🗑 Удалить мои данные",
            payload=callbacks.pack(callbacks.FORGET),
            intent=Intent.NEGATIVE,
        )
    )
    builder.row(
        CallbackButton(text="🏠 Главное меню", payload=callbacks.pack(callbacks.MENU))
    )
    return builder.as_markup()


def _confirm_keyboard() -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="Да, удалить",
            payload=callbacks.pack(callbacks.FORGET_CONFIRMED),
            intent=Intent.NEGATIVE,
        ),
        CallbackButton(text="Отмена", payload=callbacks.pack(callbacks.PRIVACY)),
    )
    return builder.as_markup()


@router.message_created(Command("privacy"))
async def on_privacy_command(event: MessageCreated, context: BaseContext) -> None:
    await render(event, context, privacy_texts.policy(), _policy_keyboard())


@router.message_callback(callbacks.is_action(callbacks.PRIVACY))
async def on_privacy(event: MessageCallback, context: BaseContext) -> None:
    await render(event, context, privacy_texts.policy(), _policy_keyboard())


@router.message_callback(callbacks.is_action(callbacks.FORGET))
async def on_forget(event: MessageCallback, context: BaseContext) -> None:
    await render(event, context, privacy_texts.confirm_forget(), _confirm_keyboard())


@router.message_callback(callbacks.is_action(callbacks.FORGET_CONFIRMED))
async def on_forget_confirmed(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    detached = await services.forget_user.execute(sender_id(event))
    data = await context.get_data()
    await context.set_state(None)
    await context.set_data({k: v for k, v in data.items() if k == SCREEN_KEY})
    await render(
        event,
        context,
        privacy_texts.forgotten(detached),
        keyboards.menu_only(),
        notification="Данные удалены",
    )
