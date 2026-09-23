"""Complaint classifier on a hosted LLM (DECISIONS D-007, Q-18).

The same `Classifier` port as the CatBoost service, so the triage use case
does not know which one is running: `CLASSIFIER=catboost|llm|rules` picks it
at startup. The model returns only the category and the emergency flag;
deadlines and legal norms stay in `SlaPolicy`, never in the model.

The model's confidence is self-reported, not calibrated. That is why it is
clamped to [0, 1] and the fail-safe stays in `TriageComplaint`: below the
threshold the resident is asked whether it is an emergency.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from application.ports.classifier import Classification, Classifier
from domain.tickets.catalog import CATEGORIES, OTHER
from infrastructure.llm.client import LLMClient, LLMUnavailableError
from infrastructure.llm.prompts import ChatMessage, extract_json
from infrastructure.ml.rule_based import RuleBasedClassifier

logger = logging.getLogger(__name__)

KNOWN_CODES = frozenset(category.code for category in (*CATEGORIES, OTHER))

SYSTEM_PROMPT = (
    "Ты классифицируешь жалобы жителей многоквартирного дома в России.\n"
    "Определи категорию и признак аварии.\n\n"
    "Категории:\n"
    + "\n".join(
        f"- {category.code}: {category.title}" for category in (*CATEGORIES, OTHER)
    )
    + "\n\n"
    "Авария (is_emergency=true) — только угроза людям или имуществу прямо "
    "сейчас: сильная течь или затопление, прорыв трубы, запах газа, искрит "
    "проводка или дым, человек застрял в лифте, нет воды, тепла или света во "
    "всём доме или подъезде. Перегоревшая лампочка, грязь, сломанный "
    "домофон, неработающий лифт без людей внутри — не авария.\n\n"
    "Уверенность — число от 0 до 1: насколько ты уверен в ответе. Если текст "
    "не про проблему дома или его нельзя понять, category=other и низкая "
    "уверенность.\n\n"
    "Ответь ТОЛЬКО одним JSON-объектом без пояснений:\n"
    '{"category": "<код>", "category_confidence": <0..1>, '
    '"is_emergency": true|false, "emergency_confidence": <0..1>}'
)


class LlmVerdict(BaseModel):
    """What the model must return; anything else is a failed call."""

    model_config = ConfigDict(extra="ignore")

    category: str
    category_confidence: float = Field(ge=0.0, le=1.0)
    is_emergency: bool
    emergency_confidence: float = Field(ge=0.0, le=1.0)


class LlmClassifier:
    """Classification by a hosted LLM with a rule-based fallback."""

    def __init__(self, client: LLMClient, fallback: Classifier | None = None) -> None:
        self._client = client
        self._fallback: Classifier = fallback or RuleBasedClassifier()

    async def classify(self, text: str) -> Classification:
        messages: list[ChatMessage] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        try:
            raw = await self._client.complete(messages)
            verdict = LlmVerdict.model_validate(extract_json(raw))
        except (LLMUnavailableError, ValueError, ValidationError) as exc:
            logger.warning("LLM classifier failed (%s), falling back to rules", exc)
            return await self._fallback.classify(text)

        if verdict.category not in KNOWN_CODES:
            logger.info("LLM returned unknown category %r", verdict.category)
            return Classification(
                category_code=OTHER.code,
                category_confidence=0.0,
                is_emergency=verdict.is_emergency,
                emergency_confidence=verdict.emergency_confidence,
            )

        return Classification(
            category_code=verdict.category,
            category_confidence=verdict.category_confidence,
            is_emergency=verdict.is_emergency,
            emergency_confidence=verdict.emergency_confidence,
        )
