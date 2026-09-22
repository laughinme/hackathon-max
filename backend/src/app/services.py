"""Сборка зависимостей приложения.

Один объект `Services` создаётся на старте и используется хендлерами.
Так их легко тестировать и позже заменить реализации (LLM, БД, API УК).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import Config
from application.ports.ai import AIService
from application.ports.classifier import Classifier
from infrastructure.ai.stub import StubAIService, get_ai_service
from infrastructure.memory.requests import RequestRepository, repository
from infrastructure.ml.catboost_classifier import CatBoostClassifier
from infrastructure.uk.client import UKClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Services:
    """Зависимости, доступные хендлерам."""

    config: Config
    uk: UKClient
    ai: AIService
    classifier: Classifier
    requests: RequestRepository
    llm_client: object | None = None


_services: Services | None = None


def build_ai(config: Config) -> tuple[AIService, object | None]:
    """Выбирает AI-слой: дообученную модель или заглушку.

    Модель обслуживается отдельным сервисом, поэтому её клиент
    создаётся лениво и импортируется только при `LLM_ENABLED=true`:
    без модели бот не тащит ML-код в рантайм.
    """

    if not config.llm_enabled:
        logger.info("AI-слой: StubAIService (заглушка)")
        return get_ai_service(), None

    from infrastructure.llm.client import LLMClient, LLMSettings
    from infrastructure.llm.service import LLMAIService

    client = LLMClient(
        LLMSettings(
            base_url=config.llm_base_url,
            model=config.llm_model,
            api_key=config.llm_api_key,
            timeout_sec=config.llm_timeout_sec,
            temperature=config.llm_temperature,
        )
    )
    logger.info(
        "AI-слой: дообученная модель %s (%s), откат — StubAIService",
        config.llm_model,
        config.llm_base_url,
    )
    return LLMAIService(client, fallback=StubAIService()), client


def build_classifier(config: Config) -> Classifier:
    """Классификатор категории и аварийности жалобы (DECISIONS D-005).

    Модели CatBoost ещё не обучены — `CatBoostClassifier` сам проверяет
    файлы по путям из конфига при первом обращении и откатывается на
    правила, если их нет. Подключение готовой модели не требует
    изменений здесь: положить файлы и перезапустить бота.
    """

    return CatBoostClassifier(
        category_model_path=config.ml_category_model_path,
        emergency_model_path=config.ml_emergency_model_path,
    )


def setup_services(config: Config) -> Services:
    """Создаёт и запоминает зависимости приложения."""

    global _services
    ai, llm_client = build_ai(config)

    _services = Services(
        config=config,
        uk=UKClient(config),
        ai=ai,
        classifier=build_classifier(config),
        requests=repository,
        llm_client=llm_client,
    )
    return _services


async def shutdown_services() -> None:
    """Закрывает сетевые ресурсы зависимостей."""

    if _services is None or _services.llm_client is None:
        return

    close = getattr(_services.llm_client, "close", None)
    if close is not None:
        await close()


def get_services() -> Services:
    """Возвращает зависимости; падает, если приложение не собрано."""

    if _services is None:
        raise RuntimeError("Сервисы не инициализированы: вызовите setup_services()")
    return _services
