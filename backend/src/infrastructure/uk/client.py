"""Интеграция с системой управляющей организации (УК).

По умолчанию работает МОДЕЛЬНАЯ (mock) интеграция: реального API
УК на хакатоне нет, и мы честно помечаем это в интерфейсе бота.

Если задать `UK_API_URL` (и снять `UK_MOCK_MODE`), тот же код уйдёт
реальным HTTP POST — контракт и обработка ошибок одинаковые.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime

import aiohttp

from app.config import Config
from domain.tickets.entities import Request

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SEC = 10


@dataclass
class SubmitResult:
    """Результат регистрации обращения во внешней системе."""

    ok: bool
    external_id: str | None = None
    is_mock: bool = True
    error: str | None = None


class UKClient:
    """Клиент подачи обращения в УК."""

    def __init__(self, config: Config) -> None:
        self._config = config

    async def submit(self, request: Request) -> SubmitResult:
        """Отправляет обращение; при сбое возвращает ошибку, а не падает."""

        if not self._config.uk_enabled:
            return await self._submit_mock(request)

        try:
            return await self._submit_real(request)
        except (TimeoutError, aiohttp.ClientError) as exc:
            logger.warning("Не удалось отправить %s в УК: %s", request.number, exc)
            return SubmitResult(
                ok=False,
                is_mock=False,
                error="Внешняя система УК недоступна",
            )

    async def _submit_mock(self, request: Request) -> SubmitResult:
        """Демо-режим: имитирует регистрацию обращения в УК."""

        await asyncio.sleep(0.4)
        external_id = f"UK-{datetime.now():%Y%m%d}-{random.randint(1000, 9999)}"
        logger.info(
            "[MOCK] Обращение %s зарегистрировано как %s",
            request.number,
            external_id,
        )
        return SubmitResult(ok=True, external_id=external_id, is_mock=True)

    async def _submit_real(self, request: Request) -> SubmitResult:
        """Боевой режим: POST в API управляющей организации."""

        headers = {}
        if self._config.uk_api_token:
            headers["Authorization"] = f"Bearer {self._config.uk_api_token}"

        payload = {
            "external_number": request.number,
            "category": request.category,
            "urgency": request.urgency,
            "text": request.text,
            "created_at": request.created_at.isoformat(),
            "applicant_id": request.user_id,
        }

        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SEC)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(
                str(self._config.uk_api_url), json=payload, headers=headers
            ) as response,
        ):
            if response.status >= 400:
                body = await response.text()
                logger.warning(
                    "УК вернула %s для %s: %s",
                    response.status,
                    request.number,
                    body[:200],
                )
                return SubmitResult(
                    ok=False,
                    is_mock=False,
                    error=f"УК вернула код {response.status}",
                )

            data = await response.json()
            return SubmitResult(
                ok=True,
                external_id=str(data.get("id") or data.get("external_id")),
                is_mock=False,
            )
