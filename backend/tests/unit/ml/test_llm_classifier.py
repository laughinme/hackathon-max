from __future__ import annotations

import json
from typing import Any, cast

import pytest

from app.config import load_config
from application.ports.classifier import Classification
from infrastructure.llm.classifier import LlmClassifier
from infrastructure.llm.client import LLMClient, LLMUnavailableError


class ScriptedClient:
    """Returns a fixed answer or raises, like `LLMClient.complete`."""

    def __init__(self, answer: str | Exception) -> None:
        self._answer = answer
        self.calls = 0

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        if isinstance(self._answer, Exception):
            raise self._answer
        return self._answer


class FixedFallback:
    async def classify(self, text: str) -> Classification:
        return Classification("fallback", 0.0, True, 0.5)


def _classifier(answer: str | Exception) -> LlmClassifier:
    client = cast(LLMClient, ScriptedClient(answer))
    return LlmClassifier(client, fallback=FixedFallback())


def _answer(**overrides: Any) -> str:
    verdict = {
        "category": "lift",
        "category_confidence": 0.93,
        "is_emergency": True,
        "emergency_confidence": 0.88,
    }
    return json.dumps({**verdict, **overrides})


async def test_valid_answer_becomes_classification() -> None:
    result = await _classifier(_answer()).classify("Застрял в лифте с ребёнком")

    assert result == Classification("lift", 0.93, True, 0.88)


async def test_json_in_markdown_fence_is_accepted() -> None:
    result = await _classifier(f"```json\n{_answer()}\n```").classify("лифт")

    assert result.category_code == "lift"


async def test_unknown_category_maps_to_other_with_zero_confidence() -> None:
    result = await _classifier(_answer(category="gas")).classify("пахнет газом")

    assert result.category_code == "other"
    assert result.category_confidence == 0.0
    assert result.is_emergency is True


@pytest.mark.parametrize(
    "answer",
    [
        "не знаю",
        _answer(category_confidence=1.7),
        json.dumps({"category": "lift"}),
        LLMUnavailableError("timeout"),
    ],
    ids=["not-json", "confidence-out-of-range", "missing-fields", "unavailable"],
)
async def test_any_failure_falls_back(answer: str | Exception) -> None:
    result = await _classifier(answer).classify("течёт труба")

    assert result.category_code == "fallback"


def test_config_rejects_unknown_classifier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_TOKEN", "t")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    monkeypatch.setenv("CLASSIFIER", "gpt")

    with pytest.raises(RuntimeError, match="CLASSIFIER"):
        load_config()


def test_config_requires_model_for_llm_classifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_TOKEN", "t")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    monkeypatch.setenv("CLASSIFIER", "llm")
    monkeypatch.delenv("LLM_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="LLM_MODEL"):
        load_config()
