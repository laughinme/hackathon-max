"""Тесты загрузки моделей: сервис не должен падать, пока их нет."""

from __future__ import annotations

from pathlib import Path

import pytest

from mlsvc.classifier import ClassifierModels, ModelsNotReadyError


def test_try_load_is_noop_when_files_are_missing(tmp_path: Path) -> None:
    models = ClassifierModels(
        category_model_path=tmp_path / "category.cbm",
        emergency_model_path=tmp_path / "emergency.cbm",
    )

    models.try_load()

    assert models.category_model_loaded is False
    assert models.emergency_model_loaded is False


def test_predict_raises_clear_error_when_not_loaded(tmp_path: Path) -> None:
    models = ClassifierModels(
        category_model_path=tmp_path / "category.cbm",
        emergency_model_path=tmp_path / "emergency.cbm",
    )

    with pytest.raises(ModelsNotReadyError):
        models.predict_category("течёт кран")

    with pytest.raises(ModelsNotReadyError):
        models.predict_emergency("течёт кран")
