"""Конфигурация ML-сервиса. Все параметры — из окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Параметры запуска сервиса классификации."""

    category_model_path: str
    emergency_model_path: str
    log_level: str


def load_config() -> Config:
    """Собирает конфиг из переменных окружения."""

    return Config(
        category_model_path=os.getenv(
            "CATEGORY_MODEL_PATH", "models/category_classifier.cbm"
        ),
        emergency_model_path=os.getenv(
            "EMERGENCY_MODEL_PATH", "models/emergency_classifier.cbm"
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
