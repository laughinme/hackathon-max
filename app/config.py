"""Конфигурация приложения. Все секреты берутся только из окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    """Параметры запуска бота."""

    bot_token: str
    log_level: str

    # Интеграция с УК. Пока работает в демо-режиме (mock).
    uk_api_url: str | None
    uk_api_token: str | None
    uk_mock_mode: bool

    # Демонстрационная автосмена статусов заявки.
    demo_status_simulation: bool
    demo_status_delay_sec: int

    @property
    def uk_enabled(self) -> bool:
        """Есть ли реальная внешняя система УК."""
        return bool(self.uk_api_url) and not self.uk_mock_mode


def load_config() -> Config:
    """Собирает конфиг из переменных окружения."""

    token = os.getenv("MAX_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Не задан MAX_BOT_TOKEN. Скопируйте .env.example в .env "
            "и укажите токен бота, полученный у @MasterBot в MAX."
        )

    uk_api_url = os.getenv("UK_API_URL", "").strip() or None

    return Config(
        bot_token=token,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        uk_api_url=uk_api_url,
        uk_api_token=os.getenv("UK_API_TOKEN", "").strip() or None,
        uk_mock_mode=_env_bool("UK_MOCK_MODE", default=uk_api_url is None),
        demo_status_simulation=_env_bool("DEMO_STATUS_SIMULATION", True),
        demo_status_delay_sec=_env_int("DEMO_STATUS_DELAY_SEC", 25),
    )
