"""Сборка зависимостей приложения.

Один объект `Services` создаётся на старте и используется хендлерами.
Так их легко тестировать и позже заменить реализации (LLM, БД, API УК).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.service import AIService, get_ai_service
from app.config import Config
from app.integrations.uk_client import UKClient
from app.storage import RequestRepository, repository


@dataclass(frozen=True)
class Services:
    """Зависимости, доступные хендлерам."""

    config: Config
    uk: UKClient
    ai: AIService
    requests: RequestRepository


_services: Services | None = None


def setup_services(config: Config) -> Services:
    """Создаёт и запоминает зависимости приложения."""

    global _services
    _services = Services(
        config=config,
        uk=UKClient(config),
        ai=get_ai_service(),
        requests=repository,
    )
    return _services


def get_services() -> Services:
    """Возвращает зависимости; падает, если приложение не собрано."""

    if _services is None:
        raise RuntimeError(
            "Сервисы не инициализированы: вызовите setup_services()"
        )
    return _services
