"""Compare complaint classifiers on a human-written test set (DECISIONS Q-18).

The CSV has a header `text,category,is_emergency` (is_emergency: 1/0 or
true/false), one complaint per row, written by people, not by the generator
the CatBoost model was trained on. Each available classifier runs over the
same rows:

    PYTHONPATH=src uv run python -m scripts.compare_classifiers eval.csv

- rules    always;
- catboost when the ml/ service answers at ML_SERVICE_URL;
- llm      when LLM_MODEL and LLM_API_KEY are set.

The key metric is emergency recall: a missed emergency gets a 7-day deadline
instead of 30 minutes. Fallbacks are switched off, so a dead service shows
up as errors instead of silently scoring as rules.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from application.ports.classifier import Classification, Classifier
from infrastructure.llm.classifier import LlmClassifier
from infrastructure.llm.client import LLMClient, LLMSettings
from infrastructure.ml.http_classifier import HttpClassifier
from infrastructure.ml.rule_based import RuleBasedClassifier


@dataclass(frozen=True)
class Sample:
    text: str
    category: str
    is_emergency: bool


class Broken(Exception):
    """Raised instead of a silent fallback, so the row counts as an error."""


class NoFallback:
    async def classify(self, text: str) -> Classification:
        raise Broken


@dataclass
class Score:
    total: int = 0
    correct_category: int = 0
    true_positive: int = 0
    false_positive: int = 0
    false_negative: int = 0
    errors: int = 0
    seconds: list[float] = field(default_factory=list)

    def add(self, sample: Sample, result: Classification, seconds: float) -> None:
        self.total += 1
        self.seconds.append(seconds)
        self.correct_category += result.category_code == sample.category
        if result.is_emergency and sample.is_emergency:
            self.true_positive += 1
        elif result.is_emergency:
            self.false_positive += 1
        elif sample.is_emergency:
            self.false_negative += 1

    def row(self, name: str) -> str:
        def ratio(part: int, whole: int) -> str:
            return f"{part / whole:.0%}" if whole else "—"

        tp = self.true_positive
        category = ratio(self.correct_category, self.total)
        recall = ratio(tp, tp + self.false_negative)
        precision = ratio(tp, tp + self.false_positive)
        latency = sorted(self.seconds)[len(self.seconds) // 2] if self.seconds else 0
        return (
            f"{name:<9}{category:>9}{recall:>11}{precision:>14}"
            f"{self.false_negative:>8}{self.errors:>8}{latency * 1000:>8.0f}"
        )


def load_samples(path: Path) -> list[Sample]:
    with path.open(encoding="utf-8") as file:
        return [
            Sample(
                text=row["text"].strip(),
                category=row["category"].strip(),
                is_emergency=row["is_emergency"].strip().lower() in {"1", "true"},
            )
            for row in csv.DictReader(file)
            if row.get("text", "").strip()
        ]


async def evaluate(classifier: Classifier, samples: list[Sample]) -> Score:
    score = Score()
    for sample in samples:
        started = time.perf_counter()
        try:
            result = await classifier.classify(sample.text)
        except Broken:
            score.errors += 1
            continue
        score.add(sample, result, time.perf_counter() - started)
    return score


async def main(path: Path) -> None:
    samples = load_samples(path)
    emergencies = sum(sample.is_emergency for sample in samples)
    print(f"{len(samples)} complaints, {emergencies} emergencies\n")

    candidates: dict[str, Classifier] = {"rules": RuleBasedClassifier()}
    closeables: list[HttpClassifier | LLMClient] = []

    catboost = HttpClassifier(
        os.getenv("ML_SERVICE_URL", "http://localhost:8100"), fallback=NoFallback()
    )
    candidates["catboost"] = catboost
    closeables.append(catboost)

    if os.getenv("LLM_MODEL") and os.getenv("LLM_API_KEY"):
        client = LLMClient(
            LLMSettings(
                base_url=os.getenv(
                    "LLM_BASE_URL", "https://ai.api.cloud.yandex.net/v1"
                ),
                model=os.environ["LLM_MODEL"],
                api_key=os.environ["LLM_API_KEY"],
                temperature=0.0,
            )
        )
        candidates["llm"] = LlmClassifier(client, fallback=NoFallback())
        closeables.append(client)

    print(
        f"{'name':<9}{'category':>9}{'em.recall':>11}{'em.precision':>14}"
        f"{'missed':>8}{'errors':>8}{'p50 ms':>8}"
    )
    try:
        for name, classifier in candidates.items():
            score = await evaluate(classifier, samples)
            print(score.row(name))
    finally:
        for resource in closeables:
            await resource.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    parser = argparse.ArgumentParser(description="Compare complaint classifiers")
    parser.add_argument("csv", type=Path)
    asyncio.run(main(parser.parse_args().csv))
