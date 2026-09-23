"""Payload'ы inline-кнопок.

Формат: `<действие>` или `<действие>:<аргумент>`.
Payload callback-кнопки в MAX ограничен 1024 символами, поэтому держим его коротким
и никогда не кладём туда пользовательский текст.
"""

from __future__ import annotations

from magic_filter import MagicFilter
from maxapi import F

MENU = "menu"
NEW = "new"
CATEGORY = "cat"
DRAFT_DONE = "draft_done"
DRAFT_RESTART = "draft_restart"
MY_LIST = "my"
MY_ITEM = "item"
EMERGENCY = "emg"
BUILDING = "bld"
CHANGE_BUILDING = "home"
DEMO_DISPATCHER = "demo_disp"
QUEUE = "dq"
QUEUE_ITEM = "dt"
QUEUE_SET = "ds"
QUEUE_SKIP_COMMENT = "dsc"
CONFIRM_FIXED = "ok"
CONFIRM_REOPEN = "reopen"
ESCALATE = "esc"
DEMO_EXPIRE = "dexp"
PRIVACY = "privacy"
FORGET = "forget"
FORGET_CONFIRMED = "forget_yes"
GROUP_BUILDING = "gbld"
GROUP_FILE = "gfile"
GROUP_DROP = "gdrop"
GROUP_SUPPORT = "gsup"
NOOP = "noop"

SEPARATOR = ":"


def pack(action: str, argument: str | int | None = None) -> str:
    """Собирает payload кнопки."""

    if argument is None:
        return action
    return f"{action}{SEPARATOR}{argument}"


def unpack(payload: str | None) -> tuple[str, str | None]:
    """Разбирает payload на действие и аргумент."""

    if not payload:
        return "", None
    action, _, argument = payload.partition(SEPARATOR)
    return action, argument or None


def is_action(action: str) -> MagicFilter:
    """Фильтр точного совпадения действия."""

    return F.callback.payload == action


def has_action(action: str) -> MagicFilter:
    """Фильтр действия с аргументом: `action:<...>`."""

    prefix = f"{action}{SEPARATOR}"
    return F.callback.payload.func(
        lambda payload: isinstance(payload, str) and payload.startswith(prefix)
    )
