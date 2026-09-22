"""HTTP-контракт сервиса — см. docs/CONTRACTS.md в корне репозитория."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClassifyRequest(BaseModel):
    """Тело запроса `POST /classify`."""

    text: str = Field(min_length=1, description="Текст жалобы жителя")


class ClassifyResponse(BaseModel):
    """Ответ `POST /classify` — вход в SlaPolicy на стороне бэкенда."""

    category_code: str
    category_confidence: float
    is_emergency: bool
    emergency_confidence: float


class ReadyResponse(BaseModel):
    """Ответ `GET /ready` — загружены ли обе модели."""

    category_model_loaded: bool
    emergency_model_loaded: bool
