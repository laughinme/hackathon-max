"""FastAPI-приложение: классификация жалоб (категория + аварийность).

Контракт — `POST /classify` (docs/CONTRACTS.md в корне репозитория).
Отдельный процесс/контейнер от бота (DECISIONS D-006): бэкенд ходит
сюда по HTTP через `infrastructure/ml/http_classifier.py` и сам
откатывается на правила, если этот сервис недоступен или модели ещё
не обучены — см. `RuleBasedClassifier` в backend/.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from mlsvc.classifier import ClassifierModels, ModelsNotReadyError
from mlsvc.config import load_config
from mlsvc.schemas import ClassifyRequest, ClassifyResponse, ReadyResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = load_config()
logging.getLogger().setLevel(config.log_level)

models = ClassifierModels(
    category_model_path=config.category_model_path,
    emergency_model_path=config.emergency_model_path,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Пробует загрузить модели на старте; без них сервис тоже поднимается."""

    models.try_load()
    if not (models.category_model_loaded and models.emergency_model_loaded):
        logger.warning(
            "Модели не найдены — /classify будет отвечать 503, пока их не положат "
            "по путям %s / %s и не перезапустят сервис",
            config.category_model_path,
            config.emergency_model_path,
        )
    yield


app = FastAPI(title="domovoy-ml", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness: процесс жив, вне зависимости от того, загружены ли модели."""

    return {"status": "ok"}


@app.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    """Readiness: готовы ли модели отвечать на /classify."""

    return ReadyResponse(
        category_model_loaded=models.category_model_loaded,
        emergency_model_loaded=models.emergency_model_loaded,
    )


@app.post("/classify", response_model=ClassifyResponse)
def classify(payload: ClassifyRequest) -> ClassifyResponse:
    """Классифицирует текст жалобы: категория + аварийность."""

    try:
        category_code, category_confidence = models.predict_category(payload.text)
        is_emergency, emergency_confidence = models.predict_emergency(payload.text)
    except ModelsNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ClassifyResponse(
        category_code=category_code,
        category_confidence=category_confidence,
        is_emergency=is_emergency,
        emergency_confidence=emergency_confidence,
    )
