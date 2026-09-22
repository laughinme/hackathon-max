"""Классификатор на правилах — работает без обученной модели.

Это резервный путь и текущая реализация по умолчанию: как только
появится обученный CatBoost (DECISIONS D-005), он подключается через
тот же порт `Classifier` без изменений в вызывающем коде — см.
`catboost_classifier.py`, который откатывается именно сюда, пока
файлов модели нет.
"""

from __future__ import annotations

from application.ports.classifier import Classification
from domain.tickets.catalog import guess_category

#: Слова, указывающие на угрозу людям/имуществу — грубый признак
#: аварийности, пока нет обученной модели. Список неполный и не
#: заменяет модель, только даёт системе не молчать до её появления.
EMERGENCY_KEYWORDS: tuple[str, ...] = (
    "топит",
    "затопил",
    "заливает",
    "прорвал",
    "хлещет",
    "искрит",
    "горит",
    "дым",
    "запах газа",
    "застрял",
    "заблокирован",
    "обрыв провод",
    "нет отопления",
    "нет воды",
    "нет света",
    "угроза",
)

#: Уверенность правил в аварийности всегда невысокая специально: это
#: сигнал, что при низкой уверенности должен включаться fallback-диалог
#: (D-005, сценарий 2), пока не появится обученная модель с реальной
#: оценкой уверенности.
EMERGENCY_CONFIDENCE_ON_RULES = 0.5


class RuleBasedClassifier:
    """Классификация по ключевым словам — работает без модели."""

    async def classify(self, text: str) -> Classification:
        category = guess_category(text)
        is_emergency = self._looks_like_emergency(text)

        return Classification(
            category_code=category.code,
            # "other" — категория не распознана; отдельно от аварийности,
            # у правил нет откалиброванной уверенности, только средняя/нулевая.
            category_confidence=0.0 if category.code == "other" else 0.7,
            is_emergency=is_emergency,
            emergency_confidence=EMERGENCY_CONFIDENCE_ON_RULES,
        )

    @staticmethod
    def _looks_like_emergency(text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in EMERGENCY_KEYWORDS)
