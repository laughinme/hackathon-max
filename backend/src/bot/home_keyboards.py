"""Keyboards of the main menu and onboarding."""

from __future__ import annotations

from maxapi.enums.intent import Intent
from maxapi.types.attachments.buttons import CallbackButton
from maxapi.types.attachments.buttons.attachment_button import AttachmentButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from application.housing.identity import Identity
from bot import callbacks
from domain.housing.entities import Building


def main_menu(identity: Identity, demo_mode: bool) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="📝 Сообщить о проблеме",
            payload=callbacks.pack(callbacks.NEW),
            intent=Intent.POSITIVE,
        )
    )
    builder.row(
        CallbackButton(text="📂 Мои заявки", payload=callbacks.pack(callbacks.MY_LIST))
    )
    if identity.dispatcher:
        builder.row(
            CallbackButton(
                text="🗂 Очередь заявок УО", payload=callbacks.pack(callbacks.QUEUE)
            )
        )
    elif demo_mode:
        builder.row(
            CallbackButton(
                text="🧑‍💼 Демо: войти как диспетчер УО",
                payload=callbacks.pack(callbacks.DEMO_DISPATCHER),
            )
        )
    home_label = "🏠 Сменить дом" if identity.residency else "🏠 Выбрать дом"
    builder.row(
        CallbackButton(
            text=home_label, payload=callbacks.pack(callbacks.CHANGE_BUILDING)
        )
    )
    return builder.as_markup()


def buildings(options: list[Building]) -> AttachmentButton:
    builder = InlineKeyboardBuilder()
    for building in options:
        builder.row(
            CallbackButton(
                text=f"🏠 {building.address}",
                payload=callbacks.pack(callbacks.BUILDING, building.code),
            )
        )
    builder.row(
        CallbackButton(text="🏠 Главное меню", payload=callbacks.pack(callbacks.MENU))
    )
    return builder.as_markup()
