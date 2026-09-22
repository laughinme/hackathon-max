"""Адаптер классификатора на CatBoost (DECISIONS D-005).

Модели обучаются офлайн, отдельно от бота, и кладутся в файлы,
которые этот адаптер лениво загружает по путям из конфига.
`catboost` не входит в основной рантайм бота (dependency-group `ml`
в pyproject.toml) — импортируется только внутри `_ensure_loaded`,
чтобы контейнер бота не тащил лишнюю зависимость, пока моделей нет.

Пока файлов моделей нет (или они не читаются) — адаптер откатывается
на `RuleBasedClassifier` и пишет предупреждение в лог. Это тот же
паттерн отказоустойчивости, что уже используется в
`infrastructure/llm/service.py` для LLM: рантайм не падает и не ждёт
ML, апгрейд происходит без изменений в вызывающем коде — просто
положить файлы моделей по путям из конфига и перезапустить бота.

Ожидает два файла модели (`category_model_path`, `emergency_model_path`)
— раздельные классификаторы, потому что учатся на разных таргетах и,
возможно, разных наборах фич (аварийность — это признаки внутри
формулировки, а не сама категория). Если в итоге обучена одна общая
модель с двумя выходами — этот класс не подходит один в один, нужен
свой адаптер с тем же протоколом `Classifier`.

Предполагается, что обе модели обучены на «сыром» тексте жалобы как
одном текстовом признаке (`text_features` в CatBoost) — `predict_proba`
здесь вызывается с одной текстовой колонкой. Если пайплайн признаков
у обученной модели другой (TF-IDF, эмбеддинги, доп. колонки) — методы
`_predict_category`/`_predict_emergency` нужно поправить под него.
"""

from __future__ import annotations

import logging
from pathlib import Path

from application.ports.classifier import Classification, Classifier
from infrastructure.ml.rule_based import RuleBasedClassifier

logger = logging.getLogger(__name__)

#: Индекс класса "авария" в бинарном классификаторе аварийности
#: (0 = не авария, 1 = авария) — таким и должен быть обучающий таргет.
EMERGENCY_CLASS_INDEX = 1


class CatBoostClassifier:
    """Классификация категории и аварийности обученными моделями CatBoost."""

    def __init__(
        self,
        category_model_path: str | Path,
        emergency_model_path: str | Path,
        fallback: Classifier | None = None,
    ) -> None:
        self._category_model_path = Path(category_model_path)
        self._emergency_model_path = Path(emergency_model_path)
        self._fallback = fallback or RuleBasedClassifier()
        self._category_model = None
        self._emergency_model = None

    async def classify(self, text: str) -> Classification:
        if not self._ensure_loaded():
            logger.warning(
                "Модели CatBoost не найдены (%s, %s) — откат на RuleBasedClassifier",
                self._category_model_path,
                self._emergency_model_path,
            )
            return await self._fallback.classify(text)

        category_code, category_confidence = self._predict_category(text)
        is_emergency, emergency_confidence = self._predict_emergency(text)

        return Classification(
            category_code=category_code,
            category_confidence=category_confidence,
            is_emergency=is_emergency,
            emergency_confidence=emergency_confidence,
        )

    def _ensure_loaded(self) -> bool:
        """Загружает модели при первом обращении. True, если обе на месте."""

        if self._category_model is not None and self._emergency_model is not None:
            return True

        if not (
            self._category_model_path.is_file()
            and self._emergency_model_path.is_file()
        ):
            return False

        # catboost — опциональная зависимость (`uv sync --group ml`),
        # ставится только когда появляются файлы моделей.
        from catboost import CatBoostClassifier as CatBoostModel  # type: ignore

        self._category_model = CatBoostModel().load_model(
            str(self._category_model_path)
        )
        self._emergency_model = CatBoostModel().load_model(
            str(self._emergency_model_path)
        )
        logger.info(
            "CatBoost-классификатор загружен: категория=%s, аварийность=%s",
            self._category_model_path,
            self._emergency_model_path,
        )
        return True

    def _predict_category(self, text: str) -> tuple[str, float]:
        assert self._category_model is not None
        probabilities = self._category_model.predict_proba([text])[0]
        classes = self._category_model.classes_
        best_index = probabilities.argmax()
        return str(classes[best_index]), float(probabilities[best_index])

    def _predict_emergency(self, text: str) -> tuple[bool, float]:
        assert self._emergency_model is not None
        probabilities = self._emergency_model.predict_proba([text])[0]
        emergency_probability = float(probabilities[EMERGENCY_CLASS_INDEX])
        return emergency_probability >= 0.5, emergency_probability
