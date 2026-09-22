"""Тесты адаптера CatBoost: откат на правила, пока моделей нет.

Тесты не требуют установленного `catboost` — путь загрузки модели
не выполняется, пока файлов по переданным путям не существует.
"""

from __future__ import annotations

from pathlib import Path

from infrastructure.ml.catboost_classifier import CatBoostClassifier


async def test_falls_back_to_rules_when_model_files_are_missing(
    tmp_path: Path,
) -> None:
    classifier = CatBoostClassifier(
        category_model_path=tmp_path / "category.cbm",
        emergency_model_path=tmp_path / "emergency.cbm",
    )

    result = await classifier.classify("не работает лифт, внутри никого нет")

    assert result.category_code == "lift"
    assert result.is_emergency is False


async def test_falls_back_when_only_one_model_file_exists(tmp_path: Path) -> None:
    category_path = tmp_path / "category.cbm"
    category_path.write_bytes(b"not a real model")

    classifier = CatBoostClassifier(
        category_model_path=category_path,
        emergency_model_path=tmp_path / "missing_emergency.cbm",
    )

    result = await classifier.classify("течёт кран на кухне")

    assert result.category_code == "water"
