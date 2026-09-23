"""Обучение → сохранение → загрузка сервисом: формат признаков один и тот же.

Модели маленькие (кусок реального датасета, десятки итераций) — тест
проверяет стыковку, а не качество.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mlsvc.classifier import ClassifierModels
from training.train import TASKS, TrainParams, run

DATA_DIR = Path(__file__).resolve().parents[1] / "dataset" / "data"
FAST = TrainParams(iterations=30, early_stopping_rounds=10, val_size=0.25)


@pytest.fixture
def small_data_dir(tmp_path: Path) -> Path:
    for split, per_class in (("train", 12), ("test", 3)):
        frame = pd.read_csv(DATA_DIR / f"{split}.csv")
        sample = frame.groupby(["category", "is_emergency"]).head(per_class)
        sample.to_csv(tmp_path / f"{split}.csv", index=False)
    return tmp_path


def test_trained_models_load_and_predict_through_service(
    small_data_dir: Path, tmp_path: Path
) -> None:
    out_dir = tmp_path / "models"

    results = run(
        ["category", "emergency"], small_data_dir, out_dir, FAST, verbose=False
    )

    assert set(results) == {"category", "emergency"}
    assert (out_dir / "metrics.json").is_file()

    models = ClassifierModels(
        category_model_path=out_dir / TASKS["category"].model_file,
        emergency_model_path=out_dir / TASKS["emergency"].model_file,
    )
    models.try_load()
    assert models.category_model_loaded and models.emergency_model_loaded

    category, category_confidence = models.predict_category("течёт кран на кухне")
    is_emergency, emergency_confidence = models.predict_emergency(
        "застрял в лифте, подъезд 4"
    )

    assert category in {
        "water",
        "light",
        "heating",
        "door",
        "cleaning",
        "lift",
        "other",
    }
    assert 0.0 <= category_confidence <= 1.0
    assert isinstance(is_emergency, bool)
    # Уверенность в решении, а не P(авария) — см. docs/CONTRACTS.md §4.
    assert 0.5 <= emergency_confidence <= 1.0
