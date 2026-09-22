"""Адаптер классификатора поверх отдельного ML-сервиса (DECISIONS D-006).

Категория и аварийность считаются не в процессе бота, а отдельным
сервисом (`ml/`, свой Docker-контейнер) — бот просто ходит к нему по
HTTP. Тот же паттерн отказоустойчивости, что уже используется для
LLM в `infrastructure/llm/service.py`: если сервис недоступен, вернул
не-200 или ещё не обучен (503 — модели не загружены), адаптер тихо
откатывается на `RuleBasedClassifier`, и бот не падает и не ждёт ML.
"""

from __future__ import annotations

import logging

import aiohttp

from application.ports.classifier import Classification, Classifier
from infrastructure.ml.rule_based import RuleBasedClassifier

logger = logging.getLogger(__name__)


class MLServiceUnavailableError(RuntimeError):
    """ML-сервис недоступен или вернул некорректный ответ."""


class HttpClassifier:
    """Классификация через HTTP-вызов отдельного ML-сервиса."""

    def __init__(
        self,
        base_url: str,
        timeout_sec: float = 3.0,
        fallback: Classifier | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_sec = timeout_sec
        self._fallback: Classifier = fallback or RuleBasedClassifier()
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout_sec)
            )
        return self._session

    async def close(self) -> None:
        """Закрывает HTTP-сессию."""

        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def classify(self, text: str) -> Classification:
        try:
            return await self._classify_remote(text)
        except MLServiceUnavailableError as exc:
            logger.warning("ML-сервис недоступен (%s) — откат на правила", exc)
            return await self._fallback.classify(text)

    async def _classify_remote(self, text: str) -> Classification:
        session = await self._ensure_session()
        url = f"{self._base_url}/classify"

        try:
            async with session.post(url, json={"text": text}) as response:
                if response.status != 200:
                    body = await response.text()
                    raise MLServiceUnavailableError(f"{response.status}: {body[:200]}")
                data = await response.json()
        except (TimeoutError, aiohttp.ClientError) as exc:
            raise MLServiceUnavailableError(str(exc)) from exc

        try:
            return Classification(
                category_code=data["category_code"],
                category_confidence=float(data["category_confidence"]),
                is_emergency=bool(data["is_emergency"]),
                emergency_confidence=float(data["emergency_confidence"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MLServiceUnavailableError(
                f"неожиданный формат ответа: {exc}"
            ) from exc
