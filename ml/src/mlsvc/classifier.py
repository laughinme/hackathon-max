"""Загрузка и инференс моделей CatBoost.

Два отдельных классификатора — категория и аварийность (DECISIONS
D-005 в корне репозитория): учатся на разных таргетах и, возможно,
разных наборах признаков. Предполагается, что обе модели обучены на
«сыром» тексте жалобы как одном текстовом признаке (`text_features`
в CatBoost) — `predict_proba` здесь вызывается с одной текстовой
колонкой. Если пайплайн признаков другой (TF-IDF, эмбеддинги, доп.
колонки) — методы `predict_category`/`predict_emergency` нужно
поправить под него.
"""

from __future__ import annotations

import logging
from pathlib import Path

from catboost import CatBoostClassifier

logger = logging.getLogger(__name__)

#: Индекс класса "авария" в бинарном классификаторе аварийности
#: (0 = не авария, 1 = авария) — таким и должен быть обучающий таргет.
EMERGENCY_CLASS_INDEX = 1


class ModelsNotReadyError(RuntimeError):
    """Файлы моделей ещё не появились по сконфигурированным путям."""


class ClassifierModels:
    """Держит обе загруженные модели и умеет их (пере)загружать."""

    def __init__(
        self,
        category_model_path: str | Path,
        emergency_model_path: str | Path,
    ) -> None:
        self._category_model_path = Path(category_model_path)
        self._emergency_model_path = Path(emergency_model_path)
        self._category_model: CatBoostClassifier | None = None
        self._emergency_model: CatBoostClassifier | None = None

    @property
    def category_model_loaded(self) -> bool:
        return self._category_model is not None

    @property
    def emergency_model_loaded(self) -> bool:
        return self._emergency_model is not None

    def try_load(self) -> None:
        """Пробует загрузить модели, если файлы уже на месте.

        Безопасно вызывать многократно (на старте и по крону) — пока
        моделей нет, просто ничего не делает и не бросает исключение,
        чтобы сервис поднимался и отвечал на /health до обучения.
        """

        if self._category_model is None and self._category_model_path.is_file():
            self._category_model = CatBoostClassifier()
            self._category_model.load_model(str(self._category_model_path))
            logger.info("Загружена модель категории: %s", self._category_model_path)

        if self._emergency_model is None and self._emergency_model_path.is_file():
            self._emergency_model = CatBoostClassifier()
            self._emergency_model.load_model(str(self._emergency_model_path))
            logger.info(
                "Загружена модель аварийности: %s", self._emergency_model_path
            )

    def predict_category(self, text: str) -> tuple[str, float]:
        if self._category_model is None:
            raise ModelsNotReadyError(
                f"Модель категории не найдена: {self._category_model_path}"
            )

        probabilities = self._category_model.predict_proba([text])[0]
        classes = self._category_model.classes_
        best_index = probabilities.argmax()
        return str(classes[best_index]), float(probabilities[best_index])

    def predict_emergency(self, text: str) -> tuple[bool, float]:
        if self._emergency_model is None:
            raise ModelsNotReadyError(
                f"Модель аварийности не найдена: {self._emergency_model_path}"
            )

        probabilities = self._emergency_model.predict_proba([text])[0]
        emergency_probability = float(probabilities[EMERGENCY_CLASS_INDEX])
        return emergency_probability >= 0.5, emergency_probability
