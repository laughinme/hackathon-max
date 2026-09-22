"""MAX webhook endpoint that always answers 200 quickly.

maxapi's stock FastAPI route parses the update inside the request, and parsing
may call the MAX API (it resolves the chat). Any failure there, or a slow MAX
API, turned into HTTP 500; MAX retries and after 8 hours without a 200 drops
the subscription. Here the request only checks the secret and schedules the
work; parsing and handling run in a background task with errors logged.
"""

from __future__ import annotations

import asyncio
import logging
from http import HTTPStatus
from secrets import compare_digest
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException, Request
from maxapi import Bot, Dispatcher
from maxapi.methods.types.getted_updates import process_update_webhook

logger = logging.getLogger(__name__)


class WebhookReceiver:
    def __init__(self, dispatcher: Dispatcher, bot: Bot, secret: str) -> None:
        self._dispatcher = dispatcher
        self._bot = bot
        self._secret = secret
        self._tasks: set[asyncio.Task[None]] = set()

    def mount(self, app: FastAPI, path: str) -> None:
        @app.post(path, include_in_schema=False)
        async def max_webhook(
            request: Request,
            x_max_bot_api_secret: Annotated[str | None, Header()] = None,
        ) -> dict[str, bool]:
            if x_max_bot_api_secret is None or not compare_digest(
                x_max_bot_api_secret, self._secret
            ):
                raise HTTPException(HTTPStatus.FORBIDDEN, "Forbidden")
            try:
                payload = await request.json()
            except ValueError as exc:
                raise HTTPException(HTTPStatus.BAD_REQUEST, "Invalid JSON") from exc
            self.schedule(payload)
            return {"ok": True}

    def schedule(self, payload: dict[str, Any]) -> None:
        task = asyncio.create_task(self._process(payload))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self, timeout: float = 10.0) -> None:
        """Let in-flight updates finish on shutdown."""

        if self._tasks:
            await asyncio.wait(self._tasks, timeout=timeout)

    async def _process(self, payload: dict[str, Any]) -> None:
        update_type = payload.get("update_type")
        try:
            event = await process_update_webhook(event_json=payload, bot=self._bot)
            if event is None:
                logger.warning("Unsupported update type %s", update_type)
                return
            await self._dispatcher.handle(event)
        except Exception:  # noqa: BLE001 - never let one update kill the receiver
            logger.exception("Failed to process update %s", update_type)
