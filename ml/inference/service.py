"""Реализация `AIService` поверх дообученной модели.

Логика рантайма:
1. собрать чат теми же промптами, на которых училась модель;
2. получить ответ и провалидировать его по `ModelDecision`;
3. при невалидном JSON — одна попытка починки с явным указанием ошибки;
4. если модель недоступна или снова сломалась — откат на `StubAIService`,
   чтобы пользовательский сценарий не вставал.
"""

from __future__ import annotations

import logging

from pydantic import ValidationError

from app.ai.schemas import Analysis, DialogTurn
from app.ai.service import AIService, StubAIService
from app.categories import get_category
from ml.prompts import (
    TASK_DIALOG,
    TASK_REFINE,
    build_messages,
    extract_json,
)
from ml.inference.client import LLMClient, LLMUnavailableError
from ml.schemas import ModelDecision

logger = logging.getLogger(__name__)

REPAIR_HINT = (
    "Предыдущий ответ не прошёл валидацию: {error}. "
    "Верни ОДИН корректный JSON-объект строго по схеме, без пояснений."
)


class LLMAIService:
    """AI-слой на дообученной модели с откатом на заглушку."""

    def __init__(
        self,
        client: LLMClient,
        fallback: AIService | None = None,
    ) -> None:
        self._client = client
        self._fallback: AIService = fallback or StubAIService()

    async def analyze(
        self,
        turns: list[DialogTurn],
        category_code: str | None = None,
    ) -> Analysis:
        """Следующий шаг диалога: уточняющий вопрос или черновик."""

        payload = {
            "turns": [
                {"role": turn.role, "text": turn.text} for turn in turns
            ],
            "category_hint": category_code,
        }

        decision = await self._decide(TASK_DIALOG, payload)
        if decision is None:
            logger.info("Откат на StubAIService: analyze")
            return await self._fallback.analyze(turns, category_code)

        return self._to_analysis(decision)

    async def refine(self, draft: str, comment: str) -> str:
        """Правка готового текста обращения по замечанию жителя."""

        payload = {"draft": draft, "comment": comment}
        decision = await self._decide(TASK_REFINE, payload)

        if decision is None or not decision.draft:
            logger.info("Откат на StubAIService: refine")
            return await self._fallback.refine(draft, comment)

        return decision.draft

    async def _decide(
        self, task: str, payload: dict
    ) -> ModelDecision | None:
        """Запрашивает решение модели с одной попыткой починки."""

        messages = build_messages(task, payload)

        try:
            raw = await self._client.complete(messages)
        except LLMUnavailableError as exc:
            logger.warning("Модель недоступна (%s): %s", task, exc)
            return None

        decision, error = self._parse(raw)
        if decision is not None:
            return decision

        logger.info("Ответ модели невалиден (%s): %s", task, error)
        repair = [
            *messages,
            {"role": "assistant", "content": raw},
            {"role": "user", "content": REPAIR_HINT.format(error=error)},
        ]

        try:
            raw_retry = await self._client.complete(repair)
        except LLMUnavailableError as exc:
            logger.warning("Починка не удалась (%s): %s", task, exc)
            return None

        decision, error = self._parse(raw_retry)
        if decision is None:
            logger.warning(
                "Модель дважды вернула невалидный ответ (%s): %s",
                task,
                error,
            )
        return decision

    @staticmethod
    def _parse(raw: str) -> tuple[ModelDecision | None, str]:
        """Разбирает и валидирует ответ модели."""

        try:
            return ModelDecision.model_validate(extract_json(raw)), ""
        except (ValueError, ValidationError) as exc:
            return None, str(exc)[:200]

    @staticmethod
    def _to_analysis(decision: ModelDecision) -> Analysis:
        """Переводит решение модели в контракт бота."""

        category = get_category(decision.category)
        is_ready = decision.action == "draft" and bool(decision.draft)

        return Analysis(
            category_code=category.code,
            title=category.title,
            responsible=category.responsible,
            urgency=decision.urgency,
            is_ready=is_ready,
            question=decision.question,
            draft=decision.draft,
            explanation=decision.explanation,
            missing_fields=list(decision.missing_slots),
        )
