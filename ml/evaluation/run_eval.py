"""Прогон валидационной выборки через обслуживаемую модель.

⚠️ Требует поднятого endpoint'а с дообученной моделью, поэтому пока
НЕ ЗАПУСКАЛСЯ. Служит приёмкой качества после обучения.

Запуск:
    python -m ml.evaluation.run_eval --base-url http://localhost:8000/v1 \
        --model smart-city-jkh
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from pydantic import ValidationError

from ml.dataset.schema import read_jsonl
from ml.evaluation.metrics import EvalCounters, score_prediction
from ml.inference.client import LLMClient, LLMSettings, LLMUnavailableError
from ml.prompts import extract_json
from ml.schemas import ModelDecision

logger = logging.getLogger(__name__)


async def evaluate(
    dataset_path: Path, client: LLMClient, limit: int | None = None
) -> dict[str, float]:
    """Считает метрики по валидационной выборке."""

    counters = EvalCounters()

    for index, example in enumerate(read_jsonl(dataset_path)):
        if limit is not None and index >= limit:
            break

        expected = ModelDecision.model_validate_json(example.target)
        dialog_text = "\n".join(m["content"] for m in example.messages)

        predicted: ModelDecision | None = None
        try:
            raw = await client.complete(example.messages)
            predicted = ModelDecision.model_validate(extract_json(raw))
        except LLMUnavailableError as exc:
            logger.warning("Пример %s: модель недоступна: %s", index, exc)
        except (ValueError, ValidationError) as exc:
            logger.info("Пример %s: невалидный ответ: %s", index, exc)

        score_prediction(counters, predicted, expected, dialog_text)

    return counters.report()


async def main_async(args: argparse.Namespace) -> None:
    client = LLMClient(
        LLMSettings(
            base_url=args.base_url,
            model=args.model,
            api_key=args.api_key,
            timeout_sec=args.timeout,
        )
    )
    try:
        report = await evaluate(args.dataset, client, args.limit)
    finally:
        await client.close()

    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Оценка качества модели")
    parser.add_argument(
        "--dataset", type=Path, default=Path("data/dataset/val.jsonl")
    )
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--model", default="smart-city-jkh")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
