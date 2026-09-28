from __future__ import annotations

import asyncio
import dataclasses

import pytest

from app.config import load_config
from app.services import build_classifier, build_llm_client
from application.ports.classifier import Classification, Classifier
from infrastructure.ml.double_check import (
    ClassifierUnavailableError,
    DoubleCheckClassifier,
    Unavailable,
)
from infrastructure.ml.http_classifier import HttpClassifier
from tests.fakes import CONFIG, StaticClassifier

THRESHOLD = 0.6
RULES = Classification("rules", 0.0, True, 0.5)


def verdict(
    category: str = "lift", emergency: bool = False, confidence: float = 0.9
) -> Classification:
    return Classification(category, 0.9, emergency, confidence)


class Down:
    async def classify(self, text: str) -> Classification:
        raise ClassifierUnavailableError


class Hanging:
    async def classify(self, text: str) -> Classification:
        await asyncio.sleep(10)
        return verdict(emergency=True)


def double_check(catboost: Classifier, llm: Classifier) -> DoubleCheckClassifier:
    return DoubleCheckClassifier(
        catboost,
        llm,
        threshold=THRESHOLD,
        llm_timeout_sec=0.05,
        fallback=StaticClassifier(RULES),
    )


async def classify(catboost: Classification, llm: Classification) -> Classification:
    classifier = double_check(StaticClassifier(catboost), StaticClassifier(llm))
    return await classifier.classify("лифт завис, внутри бабушка")


async def test_category_always_comes_from_catboost() -> None:
    result = await classify(verdict("lift"), verdict("door", True, 1.0))

    assert result.category_code == "lift"


async def test_confident_llm_raises_the_alarm_over_catboost() -> None:
    result = await classify(
        verdict(emergency=False, confidence=0.9), verdict("lift", True, 0.95)
    )

    assert result.is_emergency is True
    assert result.emergency_confidence == 0.95


@pytest.mark.parametrize(
    "llm",
    [verdict(emergency=True, confidence=0.5), verdict(emergency=False, confidence=1.0)],
    ids=["llm-unsure", "llm-says-no"],
)
async def test_llm_never_lowers_catboost(llm: Classification) -> None:
    for catboost in (
        verdict(emergency=True, confidence=0.9),
        verdict(emergency=False, confidence=0.9),
        verdict(emergency=False, confidence=0.55),  # unsure: the bot still asks
    ):
        assert await classify(catboost, llm) == catboost


async def test_agreeing_models_keep_the_higher_confidence() -> None:
    result = await classify(
        verdict(emergency=True, confidence=0.55), verdict("lift", True, 0.9)
    )

    assert result == verdict(emergency=True, confidence=0.9)


@pytest.mark.parametrize("broken_llm", [Down(), Hanging()], ids=["down", "too-slow"])
async def test_without_llm_it_is_plain_catboost(broken_llm: Classifier) -> None:
    catboost = verdict("water", emergency=False, confidence=0.9)

    result = await double_check(StaticClassifier(catboost), broken_llm).classify("x")

    assert result == catboost


async def test_without_ml_service_the_llm_answers_alone() -> None:
    llm = verdict("water", emergency=True, confidence=0.8)

    result = await double_check(Down(), StaticClassifier(llm)).classify("x")

    assert result == llm


async def test_dead_ml_service_reports_failure_instead_of_rules() -> None:
    http = HttpClassifier("http://127.0.0.1:1", timeout_sec=1.0, fallback=Unavailable())
    llm = verdict("water", emergency=True, confidence=0.8)

    try:
        result = await double_check(http, StaticClassifier(llm)).classify("x")
    finally:
        await http.close()

    assert result == llm


async def test_without_both_it_falls_back_to_rules() -> None:
    assert await double_check(Down(), Down()).classify("x") == RULES


async def test_config_builds_the_double_check() -> None:
    config = dataclasses.replace(CONFIG, classifier="catboost+llm", llm_model="m")
    client = build_llm_client(config)
    assert client is not None

    classifier, resource = build_classifier(config, client)

    assert isinstance(classifier, DoubleCheckClassifier)
    assert resource is not None
    await resource.close()
    await client.close()


def test_double_check_requires_llm_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_TOKEN", "t")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    monkeypatch.setenv("CLASSIFIER", "catboost+llm")
    monkeypatch.delenv("LLM_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="LLM_MODEL"):
        load_config()
