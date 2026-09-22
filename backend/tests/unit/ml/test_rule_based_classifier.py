"""Тесты резервного классификатора на правилах (без обученной модели)."""

from __future__ import annotations

import pytest

from infrastructure.ml.rule_based import RuleBasedClassifier


@pytest.fixture
def classifier() -> RuleBasedClassifier:
    return RuleBasedClassifier()


async def test_recognizes_category_by_keyword(classifier: RuleBasedClassifier) -> None:
    result = await classifier.classify("не работает лифт, застрял между этажами")

    assert result.category_code == "lift"
    assert result.category_confidence > 0


async def test_unknown_text_falls_back_to_other(
    classifier: RuleBasedClassifier,
) -> None:
    result = await classifier.classify("совершенно непонятная жалоба ни о чём")

    assert result.category_code == "other"
    assert result.category_confidence == 0.0


async def test_emergency_keyword_is_detected(classifier: RuleBasedClassifier) -> None:
    result = await classifier.classify(
        "прорвало трубу, топит весь подъезд, вода уже на лестнице"
    )

    assert result.is_emergency is True


async def test_routine_complaint_is_not_emergency(
    classifier: RuleBasedClassifier,
) -> None:
    result = await classifier.classify("в подъезде немного грязно, давно не убирались")

    assert result.is_emergency is False


async def test_emergency_confidence_is_deliberately_low(
    classifier: RuleBasedClassifier,
) -> None:
    """Низкая уверенность у правил — сигнал для fallback-диалога (D-005)."""

    result = await classifier.classify("лифт застрял, внутри человек")

    assert result.emergency_confidence < 0.6
