"""Контракт модели: строгий JSON, который она обязана возвращать.

Модель не разговаривает свободным текстом — она возвращает решение:
либо задать следующий уточняющий вопрос, либо сформировать обращение.
Всё остальное (тексты экранов, кнопки, статусы) строит бот.

Схема одновременно является:
- целевым форматом обучающей выборки (`ml/dataset`);
- валидатором ответа модели в рантайме (`ml/inference`);
- основой метрик качества (`ml/evaluation`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Что модель решает сделать на текущем шаге диалога.
Action = Literal["ask", "draft"]

#: Срочность в терминах, понятных управляющей организации.
Urgency = Literal["низкая", "обычная", "высокая", "аварийная"]

#: Слоты — факты, без которых обращение нельзя считать полным.
SLOT_TITLES: dict[str, str] = {
    "location": "где именно (подъезд, этаж, квартира)",
    "problem": "что именно происходит",
    "started_at": "когда началось",
    "severity": "насколько серьёзно, есть ли угроза",
    "access": "как попасть на место / контакт для доступа",
}

#: Слоты, обязательные для любой категории.
REQUIRED_SLOTS: tuple[str, ...] = ("problem", "location", "started_at")

#: Дополнительные обязательные слоты для отдельных категорий.
CATEGORY_REQUIRED_SLOTS: dict[str, tuple[str, ...]] = {
    "water": ("severity",),
    "heating": ("severity",),
    "light": ("severity",),
    "lift": ("severity",),
}


def required_slots(category: str) -> tuple[str, ...]:
    """Полный список обязательных слотов для категории."""

    return REQUIRED_SLOTS + CATEGORY_REQUIRED_SLOTS.get(category, ())


class Slots(BaseModel):
    """Факты, собранные из диалога с жителем."""

    model_config = ConfigDict(extra="ignore")

    problem: str | None = None
    location: str | None = None
    started_at: str | None = None
    severity: str | None = None
    access: str | None = None

    def filled(self) -> set[str]:
        """Имена заполненных слотов."""

        return {
            name for name, value in self.model_dump().items() if value not in (None, "")
        }

    def missing(self, category: str) -> list[str]:
        """Каких обязательных слотов не хватает для категории."""

        return [slot for slot in required_slots(category) if slot not in self.filled()]


class ModelDecision(BaseModel):
    """Ответ модели на одном шаге диалога."""

    model_config = ConfigDict(extra="ignore")

    action: Action = Field(
        description="ask — задать вопрос, draft — сформировать обращение"
    )
    category: str = Field(description="код категории проблемы")
    urgency: Urgency = "обычная"
    slots: Slots = Field(default_factory=Slots)
    missing_slots: list[str] = Field(default_factory=list)
    question: str | None = Field(
        default=None, description="один вопрос жителю, если action == ask"
    )
    draft: str | None = Field(
        default=None, description="текст обращения, если action == draft"
    )
    explanation: str = Field(default="", description="кто отвечает и что будет дальше")

    @model_validator(mode="after")
    def _check_action_payload(self) -> ModelDecision:
        """Действие обязано быть подкреплено содержимым."""

        if self.action == "ask" and not (self.question or "").strip():
            raise ValueError("action='ask' требует непустого question")

        if self.action == "draft" and not (self.draft or "").strip():
            raise ValueError("action='draft' требует непустого draft")

        return self

    def as_training_target(self) -> str:
        """Каноничный JSON для обучающей выборки и разбора ответа."""

        return self.model_dump_json(exclude_none=False, indent=None)
