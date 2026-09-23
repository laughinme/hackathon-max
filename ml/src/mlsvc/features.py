"""Единый формат признаков для обучения и инференса.

И `training/train.py`, и `classifier.py` строят вход модели только через
`to_frame` — если формат разъедется, модель молча начнёт предсказывать
мусор. Тест `tests/test_training.py` обучает маленькую модель и прогоняет
её через сервис, чтобы это ловилось сразу.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd

TEXT_FEATURE = "text"

# Токенизатор по умолчанию в CatBoost режет только по пробелу и не
# приводит к нижнему регистру: «Подъезде!» и «подъезде» — разные токены.
# BySense отделяет пунктуацию, Letter-триграммы держат опечатки
# («Крн на кухне»), которых в датасете много (стиль typo/voice).
TEXT_PROCESSING: dict[str, Any] = {
    "tokenizers": [
        {
            "tokenizer_id": "Sense",
            "separator_type": "BySense",
            "lowercasing": "true",
        }
    ],
    "dictionaries": [
        {"dictionary_id": "Word", "gram_order": "1", "occurrence_lower_bound": "2"},
        {"dictionary_id": "BiGram", "gram_order": "2", "occurrence_lower_bound": "2"},
        {
            "dictionary_id": "Trigram",
            "token_level_type": "Letter",
            "gram_order": "3",
            "occurrence_lower_bound": "3",
        },
    ],
    "feature_processing": {
        "default": [
            {
                "dictionaries_names": ["Word", "BiGram", "Trigram"],
                "feature_calcers": ["BoW"],
                "tokenizers_names": ["Sense"],
            },
            {
                "dictionaries_names": ["Word"],
                "feature_calcers": ["NaiveBayes"],
                "tokenizers_names": ["Sense"],
            },
        ]
    },
}


def to_frame(texts: Sequence[str]) -> pd.DataFrame:
    """Тексты жалоб → таблица признаков в том виде, на котором учится модель.

    Всегда двумерная (строка на объект): список строк CatBoost трактует как
    ОДИН объект и возвращает одномерный `predict_proba`.
    """

    return pd.DataFrame({TEXT_FEATURE: [str(text) for text in texts]})
