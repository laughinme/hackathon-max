"""Загрузка и инференс моделей CatBoost.

Два отдельных классификатора — категория и аварийность (DECISIONS
D-005 в корне репозитория). Обучаются скриптом `training/train.py`;
формат входа задаёт `features.to_frame`, общий для обучения и сервиса.
"""

from __future__ import annotations

import logging
from pathlib import Path

from catboost import CatBoostClassifier

from mlsvc.features import to_frame

logger = logging.getLogger(__name__)

#: Метка класса «авария» в модели аварийности (таргет is_emergency: 0/1).
EMERGENCY_LABEL = 1


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
            logger.info("Загружена модель аварийности: %s", self._emergency_model_path)

    def predict_category(self, text: str) -> tuple[str, float]:
        if self._category_model is None:
            raise ModelsNotReadyError(
                f"Модель категории не найдена: {self._category_model_path}"
            )

        probabilities = self._category_model.predict_proba(to_frame([text]))[0]
        classes = self._category_model.classes_
        best_index = int(probabilities.argmax())
        return str(classes[best_index]), float(probabilities[best_index])

    def predict_emergency(self, text: str) -> tuple[bool, float]:
        if self._emergency_model is None:
            raise ModelsNotReadyError(
                f"Модель аварийности не найдена: {self._emergency_model_path}"
            )

        probabilities = self._emergency_model.predict_proba(to_frame([text]))[0]
        classes = [int(label) for label in self._emergency_model.classes_]
        emergency_probability = float(probabilities[classes.index(EMERGENCY_LABEL)])
        is_emergency = emergency_probability >= 0.5
        # Уверенность в принятом решении, а не P(авария): бэкенд сравнивает её
        # с порогом fallback-диалога, и уверенное «не авария» (P=0.01) не должно
        # выглядеть как сомнение и включать fail-safe.
        confidence = (
            emergency_probability if is_emergency else 1 - emergency_probability
        )
        return is_emergency, confidence
