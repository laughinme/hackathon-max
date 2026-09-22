"""Уведомления об изменении статуса обращения.

Для демонстрации сценария «статус меняется → житель узнаёт об этом»
используется модельный планировщик: он двигает статус заявки и шлёт
сообщение в чат. В боевой версии сюда придут вебхуки от системы УК.
"""

from __future__ import annotations

import asyncio
import logging

from maxapi import Bot
from maxapi.exceptions import MaxError

from bot import texts
from domain.tickets.entities import Request, RequestStatus

logger = logging.getLogger(__name__)

#: Цепочка статусов для демо-режима.
DEMO_FLOW: tuple[RequestStatus, ...] = (
    RequestStatus.ACCEPTED,
    RequestStatus.IN_PROGRESS,
)

_tasks: set[asyncio.Task] = set()


def schedule_demo_status_flow(bot: Bot, request: Request, delay_sec: int) -> None:
    """Запускает фоновую имитацию движения заявки по статусам."""

    task = asyncio.create_task(_run_flow(bot, request, delay_sec))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _run_flow(bot: Bot, request: Request, delay_sec: int) -> None:
    """Последовательно меняет статус и уведомляет заявителя."""

    try:
        for status in DEMO_FLOW:
            await asyncio.sleep(delay_sec)

            if request.status in {RequestStatus.DONE, RequestStatus.REJECTED}:
                return

            request.set_status(status, comment="Демо-режим")
            await notify_status(bot, request)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Сбой демо-сценария статусов %s", request.number)


async def notify_status(bot: Bot, request: Request) -> None:
    """Отправляет уведомление о новом статусе обращения."""

    if request.chat_id is None:
        return

    try:
        await bot.send_message(
            chat_id=request.chat_id,
            text=texts.status_changed(request),
        )
    except MaxError as exc:
        logger.warning("Не удалось уведомить по %s: %s", request.number, exc)


async def shutdown() -> None:
    """Останавливает фоновые задачи при выключении бота."""

    for task in list(_tasks):
        task.cancel()
    if _tasks:
        await asyncio.gather(*_tasks, return_exceptions=True)
