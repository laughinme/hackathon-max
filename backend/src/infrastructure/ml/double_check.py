"""CatBoost with an LLM second opinion on emergencies (DECISIONS Q-18).

`CLASSIFIER=catboost+llm`. Both models run in parallel on every complaint:

- the category comes from CatBoost (94% on the test set, 3 ms, no API cost);
- the LLM can only raise the alarm: a confident "emergency" from it wins over
  CatBoost's "no", while its "no" or "not sure" never lowers CatBoost's answer.
  On ml/dataset/data/test.csv this cut missed emergencies from 6 (CatBoost) and
  7 (LLM) to 2: CatBoost missed "the lift is stuck with a grandmother inside"
  and "the garbage chute is on fire", the LLM caught both.

Degradation: without the LLM (down, slow, out of money) it is plain CatBoost;
without the ML service the LLM answers alone; without both, keyword rules.
The inner classifiers must report failure by raising (pass `Unavailable` as
their fallback), otherwise a silent fallback would look like a real answer.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
from collections.abc import Awaitable

from application.ports.classifier import Classification, Classifier
from infrastructure.ml.rule_based import RuleBasedClassifier

logger = logging.getLogger(__name__)


class ClassifierUnavailableError(RuntimeError):
    """An inner classifier could not answer."""


class Unavailable:
    """Fallback for the inner classifiers: report the failure, don't guess."""

    async def classify(self, text: str) -> Classification:
        raise ClassifierUnavailableError


class DoubleCheckClassifier:
    """Category from CatBoost; emergency if CatBoost or a confident LLM says so."""

    def __init__(
        self,
        catboost: Classifier,
        llm: Classifier,
        *,
        threshold: float,
        llm_timeout_sec: float = 5.0,
        fallback: Classifier | None = None,
    ) -> None:
        self._catboost = catboost
        self._llm = llm
        self._threshold = threshold
        self._llm_timeout_sec = llm_timeout_sec
        self._fallback: Classifier = fallback or RuleBasedClassifier()

    async def classify(self, text: str) -> Classification:
        primary, second = await asyncio.gather(
            self._ask("CatBoost", self._catboost.classify(text)),
            self._ask(
                "LLM",
                asyncio.wait_for(self._llm.classify(text), self._llm_timeout_sec),
            ),
        )
        if primary is not None and second is not None:
            return self._merge(primary, second)
        if primary is not None:
            return primary
        if second is not None:
            return second
        return await self._fallback.classify(text)

    def _merge(self, primary: Classification, second: Classification) -> Classification:
        raises_alarm = (
            second.is_emergency and second.emergency_confidence >= self._threshold
        )
        if not raises_alarm:
            return primary
        if not primary.is_emergency:
            logger.info(
                "LLM raised an emergency over CatBoost (%.2f)",
                second.emergency_confidence,
            )
            return dataclasses.replace(
                primary,
                is_emergency=True,
                emergency_confidence=second.emergency_confidence,
            )
        return dataclasses.replace(
            primary,
            emergency_confidence=max(
                primary.emergency_confidence, second.emergency_confidence
            ),
        )

    @staticmethod
    async def _ask(name: str, call: Awaitable[Classification]) -> Classification | None:
        try:
            return await call
        except Exception as exc:  # noqa: BLE001 - any failure means "no answer"
            logger.warning("%s classifier unavailable: %r", name, exc)
            return None
