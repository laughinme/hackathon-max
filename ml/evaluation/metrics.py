"""Метрики качества модели.

Метрики выбраны под продуктовую задачу, а не под «красивый loss»:
нас интересует, доходит ли житель до корректного обращения и
не выдумывает ли модель факты.

Метрики считаются пошагово по валидационной выборке. Длина диалога
(сколько вопросов до готового обращения) измеряется отдельно —
роллаутом с имитацией ответов жителя; см. ml/README.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ml.schemas import ModelDecision, Slots

#: Признаки выдуманных нормативных ссылок в тексте обращения.
NORMATIVE_PATTERNS = (
    r"\bПП\s?РФ\b",
    r"\bпостановлени[ея]\b",
    r"\bГОСТ\b",
    r"\bСанПиН\b",
    r"\bстать[яи]\s?\d+",
    r"\bп\.\s?\d+\.\d+",
)


@dataclass
class EvalCounters:
    """Накопитель результатов прогона."""

    total: int = 0
    parsed: int = 0
    valid_schema: int = 0
    action_match: int = 0
    slot_hits: int = 0
    slot_predicted: int = 0
    slot_expected: int = 0
    invented_norms: int = 0
    empty_questions: int = 0

    def report(self) -> dict[str, float]:
        """Сводка метрик в понятных числах."""

        def share(part: int) -> float:
            return round(part / self.total, 3) if self.total else 0.0

        precision = (
            self.slot_hits / self.slot_predicted
            if self.slot_predicted
            else 0.0
        )
        recall = (
            self.slot_hits / self.slot_expected
            if self.slot_expected
            else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )

        return {
            "examples": self.total,
            "json_parsed": share(self.parsed),
            "schema_valid": share(self.valid_schema),
            "action_accuracy": share(self.action_match),
            "slot_precision": round(precision, 3),
            "slot_recall": round(recall, 3),
            "slot_f1": round(f1, 3),
            "invented_norms": share(self.invented_norms),
            "empty_questions": share(self.empty_questions),
        }


def has_invented_norms(draft: str, dialog_text: str) -> bool:
    """Ссылается ли текст на нормы, которых не было в диалоге."""

    for pattern in NORMATIVE_PATTERNS:
        if re.search(pattern, draft, flags=re.IGNORECASE) and not re.search(
            pattern, dialog_text, flags=re.IGNORECASE
        ):
            return True
    return False


def slot_overlap(predicted: Slots, expected: Slots) -> tuple[int, int, int]:
    """Совпадения слотов: (попаданий, предсказано, ожидалось).

    Сравнение мягкое: слот считается угаданным, если значения
    пересекаются по нормализованной подстроке — житель и модель
    формулируют одно и то же разными словами.
    """

    def normalize(value: str | None) -> str:
        return re.sub(r"[^\w\s]", "", (value or "").lower()).strip()

    predicted_data = predicted.model_dump()
    expected_data = expected.model_dump()

    hits = 0
    predicted_count = 0
    expected_count = 0

    for name, expected_value in expected_data.items():
        predicted_value = normalize(predicted_data.get(name))
        expected_normalized = normalize(expected_value)

        if predicted_value:
            predicted_count += 1
        if expected_normalized:
            expected_count += 1

        if not predicted_value or not expected_normalized:
            continue

        if (
            predicted_value in expected_normalized
            or expected_normalized in predicted_value
        ):
            hits += 1

    return hits, predicted_count, expected_count


def score_prediction(
    counters: EvalCounters,
    predicted: ModelDecision | None,
    expected: ModelDecision,
    dialog_text: str,
) -> None:
    """Учитывает один пример в накопителе метрик."""

    counters.total += 1

    if predicted is None:
        return

    counters.parsed += 1
    counters.valid_schema += 1

    if predicted.action == expected.action:
        counters.action_match += 1

    hits, predicted_count, expected_count = slot_overlap(
        predicted.slots, expected.slots
    )
    counters.slot_hits += hits
    counters.slot_predicted += predicted_count
    counters.slot_expected += expected_count

    if predicted.action == "ask" and not (predicted.question or "").strip():
        counters.empty_questions += 1

    if predicted.action == "draft" and predicted.draft:
        if has_invented_norms(predicted.draft, dialog_text):
            counters.invented_norms += 1
