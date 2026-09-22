"""Сборка обучающей выборки в JSONL.

Запуск:
    python -m ml.dataset.build --count 2000 --out data/dataset

Создаёт `train.jsonl` и `val.jsonl`. Разбиение идёт по диалогам
(по полю meta.category и порядку генерации), чтобы шаги одного
диалога не оказались в разных частях выборки.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ml.dataset.schema import TrainingExample, write_jsonl
from ml.dataset.synthetic import generate

DEFAULT_OUT = Path("data/dataset")
DEFAULT_COUNT = 2000
DEFAULT_VAL_SHARE = 0.1


def split(
    examples: list[TrainingExample], val_share: float
) -> tuple[list[TrainingExample], list[TrainingExample]]:
    """Делит выборку на train/val без перемешивания шагов диалога."""

    if not 0 < val_share < 1:
        raise ValueError("val_share должен быть в интервале (0, 1)")

    val_size = max(1, int(len(examples) * val_share))
    boundary = len(examples) - val_size

    # Не разрываем диалог: сдвигаем границу до конца текущего диалога.
    while boundary < len(examples) and examples[boundary].meta.get(
        "step"
    ) not in {"ask", None}:
        boundary += 1

    return examples[:boundary], examples[boundary:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Сборка выборки для SFT")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-share", type=float, default=DEFAULT_VAL_SHARE)
    args = parser.parse_args()

    examples = generate(args.count, seed_value=args.seed)
    train, val = split(examples, args.val_share)

    train_count = write_jsonl(args.out / "train.jsonl", train)
    val_count = write_jsonl(args.out / "val.jsonl", val)

    print(f"train: {train_count} примеров → {args.out / 'train.jsonl'}")
    print(f"val:   {val_count} примеров → {args.out / 'val.jsonl'}")
    print(
        "⚠️ Это синтетический bootstrap. Перед финальным обучением "
        "добавьте реальные и вручную проверенные диалоги."
    )


if __name__ == "__main__":
    main()
