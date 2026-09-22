"""Клиент дообученной модели.

Модель обслуживается отдельно (vLLM / TGI) за OpenAI-совместимым
endpoint'ом, а бот ходит в неё по HTTP. Так рантайм бота остаётся
лёгким: в контейнере с ботом нет ни torch, ни весов модели.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import aiohttp

from ml.prompts import ChatMessage

logger = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    """Модель недоступна или вернула некорректный ответ."""


@dataclass(frozen=True)
class LLMSettings:
    """Параметры обращения к модели."""

    base_url: str
    model: str
    api_key: str | None = None
    timeout_sec: float = 20.0
    temperature: float = 0.2
    max_tokens: int = 700


class LLMClient:
    """Тонкий HTTP-клиент OpenAI-совместимого endpoint'а."""

    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=self._settings.timeout_sec
                )
            )
        return self._session

    async def close(self) -> None:
        """Закрывает HTTP-сессию."""

        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def complete(self, messages: list[ChatMessage]) -> str:
        """Возвращает сырой текст ответа модели."""

        payload = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": self._settings.temperature,
            "max_tokens": self._settings.max_tokens,
            # Модель обучена отвечать JSON; просим сервер это гарантировать.
            "response_format": {"type": "json_object"},
        }

        headers = {}
        if self._settings.api_key:
            headers["Authorization"] = f"Bearer {self._settings.api_key}"

        url = f"{self._settings.base_url.rstrip('/')}/chat/completions"
        session = await self._ensure_session()

        try:
            async with session.post(
                url, json=payload, headers=headers
            ) as response:
                if response.status >= 400:
                    body = await response.text()
                    raise LLMUnavailableError(
                        f"Модель вернула {response.status}: {body[:200]}"
                    )
                data = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise LLMUnavailableError(f"Модель недоступна: {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMUnavailableError(
                "Неожиданный формат ответа модели"
            ) from exc

    async def health(self) -> bool:
        """Проверяет доступность модели на старте бота."""

        try:
            await self.complete(
                [{"role": "user", "content": 'Ответь JSON {"ok": true}'}]
            )
        except LLMUnavailableError as exc:
            logger.warning("Проверка модели не прошла: %s", exc)
            return False
        return True
