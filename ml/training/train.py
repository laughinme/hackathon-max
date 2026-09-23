"""Обучение CatBoost-классификаторов категории и аварийности (DECISIONS D-005).

Учится на `dataset/data/train.csv`, ранняя остановка — на валидации,
отрезанной от train (стратифицированно). `test.csv` — фиксированный
бенчмарк: в обучении и подборе итераций не участвует, по нему только
считаются итоговые метрики.

На выходе в `models/` (том сервиса в compose.yaml):
- `category_classifier.cbm`, `emergency_classifier.cbm` — то, что грузит
  `mlsvc.classifier`; сервис подхватит их после перезапуска;
- `metrics.json` — метрики на test и параметры запуска.

Запуск:
    cd ml
    uv sync --group train
    PYTHONPATH=src uv run python training/train.py
    PYTHONPATH=src uv run python training/train.py --task emergency --iterations 2000
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split

from mlsvc.features import TEXT_FEATURE, TEXT_PROCESSING, to_frame

ML_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ML_ROOT / "dataset" / "data"
DEFAULT_OUT_DIR = ML_ROOT / "models"

#: Порог уверенности бэкенда для fallback-диалога (ML_CONFIDENCE_THRESHOLD).
#: Считаем, какая доля test ушла бы в уточнение — ориентир для подбора порога.
BACKEND_CONFIDENCE_THRESHOLD = 0.6
EMERGENCY_THRESHOLD = 0.5


@dataclass(frozen=True)
class Task:
    name: str
    target: str
    loss_function: str
    report_metric: str
    model_file: str


# Ранняя остановка — по loss, а не по F1: F1 выходит на плато за десяток
# итераций, пока вероятности ещё «плоские», и почти треть жалоб оказывалась
# ниже порога уверенности бэкенда (ушла бы в fallback-диалог без нужды).
TASKS: dict[str, Task] = {
    "category": Task(
        name="category",
        target="category",
        loss_function="MultiClass",
        report_metric="TotalF1:average=Macro",
        model_file="category_classifier.cbm",
    ),
    "emergency": Task(
        name="emergency",
        target="is_emergency",
        loss_function="Logloss",
        report_metric="F1",
        model_file="emergency_classifier.cbm",
    ),
}


@dataclass(frozen=True)
class TrainParams:
    iterations: int = 3000
    learning_rate: float | None = None
    depth: int = 6
    early_stopping_rounds: int = 150
    val_size: float = 0.15
    seed: int = 42


def load_split(data_dir: Path, split: str) -> pd.DataFrame:
    frame = pd.read_csv(data_dir / f"{split}.csv")
    missing = {"text", "category", "is_emergency"} - set(frame.columns)
    if missing:
        raise ValueError(f"{split}.csv: нет колонок {sorted(missing)}")
    return frame


def _pool(frame: pd.DataFrame, target: str) -> Pool:
    return Pool(
        to_frame(frame["text"].tolist()),
        label=frame[target].tolist(),
        text_features=[TEXT_FEATURE],
    )


def train_model(
    task: Task,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    params: TrainParams,
    verbose: int | bool = 100,
) -> CatBoostClassifier:
    model = CatBoostClassifier(
        loss_function=task.loss_function,
        eval_metric=task.loss_function,
        custom_metric=[task.report_metric],
        iterations=params.iterations,
        learning_rate=params.learning_rate,
        depth=params.depth,
        random_seed=params.seed,
        text_processing=TEXT_PROCESSING,
        early_stopping_rounds=params.early_stopping_rounds,
        use_best_model=True,
        allow_writing_files=False,
        verbose=verbose,
    )
    model.fit(
        _pool(train_df, task.target),
        eval_set=_pool(val_df, task.target),
    )
    return model


def predict_like_service(
    task: Task, model: CatBoostClassifier, texts: list[str]
) -> tuple[list[Any], list[float]]:
    """Предсказания ровно так, как их делает `mlsvc.classifier` в сервисе."""

    probabilities = model.predict_proba(to_frame(texts))
    classes = list(model.classes_)

    if task.name == "category":
        best = probabilities.argmax(axis=1)
        labels = [str(classes[i]) for i in best]
        confidences = [
            float(row[i]) for row, i in zip(probabilities, best, strict=True)
        ]
        return labels, confidences

    emergency_index = [int(c) for c in classes].index(1)
    emergency_proba = probabilities[:, emergency_index]
    labels = [int(p >= EMERGENCY_THRESHOLD) for p in emergency_proba]
    confidences = [float(max(p, 1 - p)) for p in emergency_proba]
    return labels, confidences


def evaluate(
    task: Task, model: CatBoostClassifier, test_df: pd.DataFrame
) -> dict[str, Any]:
    y_true = test_df[task.target].tolist()
    y_pred, confidences = predict_like_service(task, model, test_df["text"].tolist())
    labels = sorted(set(y_true) | set(y_pred))

    metrics: dict[str, Any] = {
        "test_size": len(y_true),
        "best_iteration": model.get_best_iteration(),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro")), 4),
        "share_below_confidence": {
            "threshold": BACKEND_CONFIDENCE_THRESHOLD,
            "share": round(
                sum(c < BACKEND_CONFIDENCE_THRESHOLD for c in confidences)
                / len(confidences),
                4,
            ),
        },
        "report": classification_report(
            y_true, y_pred, labels=labels, output_dict=True, zero_division=0
        ),
        "confusion_matrix": {
            "labels": [str(label) for label in labels],
            "matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        },
    }
    if task.name == "emergency":
        # Пропущенная авария дороже ложной тревоги (fail-safe в D-005).
        report = metrics["report"]["1"]
        metrics["emergency_recall"] = round(float(report["recall"]), 4)
        metrics["emergency_precision"] = round(float(report["precision"]), 4)
    return metrics


def print_summary(task: Task, metrics: dict[str, Any]) -> None:
    print(f"\n=== {task.name}: test ({metrics['test_size']} строк) ===")
    print(f"best_iteration: {metrics['best_iteration']}")
    print(f"accuracy: {metrics['accuracy']}  f1_macro: {metrics['f1_macro']}")
    if task.name == "emergency":
        print(
            f"recall аварий: {metrics['emergency_recall']}  "
            f"precision аварий: {metrics['emergency_precision']}"
        )
    low = metrics["share_below_confidence"]
    print(f"доля ниже уверенности {low['threshold']}: {low['share']}")
    cm = metrics["confusion_matrix"]
    print("confusion matrix (строки — истина, столбцы — прогноз):")
    print(pd.DataFrame(cm["matrix"], index=cm["labels"], columns=cm["labels"]))


def run(
    task_names: list[str],
    data_dir: Path,
    out_dir: Path,
    params: TrainParams,
    verbose: int | bool = 100,
) -> dict[str, Any]:
    train_full = load_split(data_dir, "train")
    test_df = load_split(data_dir, "test")
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {}
    for name in task_names:
        task = TASKS[name]
        train_df, val_df = train_test_split(
            train_full,
            test_size=params.val_size,
            stratify=train_full[task.target],
            random_state=params.seed,
        )
        model = train_model(task, train_df, val_df, params, verbose=verbose)
        model_path = out_dir / task.model_file
        model.save_model(str(model_path))

        metrics = evaluate(task, model, test_df)
        metrics.update(
            model_file=task.model_file,
            train_size=len(train_df),
            val_size=len(val_df),
        )
        print_summary(task, metrics)
        print(f"сохранено: {model_path}")
        results[name] = metrics

    _write_metrics(out_dir / "metrics.json", results, params)
    return results


def _write_metrics(path: Path, results: dict[str, Any], params: TrainParams) -> None:
    previous: dict[str, Any] = {}
    if path.is_file():
        previous = json.loads(path.read_text(encoding="utf-8")).get("tasks", {})
    payload = {
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "params": asdict(params),
        "tasks": {**previous, **results},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--task", choices=["category", "emergency", "all"], default="all"
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--iterations", type=int, default=TrainParams.iterations)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--depth", type=int, default=TrainParams.depth)
    parser.add_argument("--val-size", type=float, default=TrainParams.val_size)
    parser.add_argument("--seed", type=int, default=TrainParams.seed)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # консоль Windows (cp1251)
    args = parse_args(argv)
    tasks = list(TASKS) if args.task == "all" else [args.task]
    params = TrainParams(
        iterations=args.iterations,
        learning_rate=args.learning_rate,
        depth=args.depth,
        val_size=args.val_size,
        seed=args.seed,
    )
    run(tasks, args.data_dir, args.out_dir, params)


if __name__ == "__main__":
    main()
