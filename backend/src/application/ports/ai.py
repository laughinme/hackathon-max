"""Структуры данных AI-слоя.

AI обязан возвращать валидируемый структурированный результат,
а не свободный текст: на его основе строится вся дальнейшая логика.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

Role = Literal["user", "bot"]


@dataclass
class DialogTurn:
    """Одна реплика диалога уточнения."""

    role: Role
    text: str


@dataclass
class Analysis:
    """Результат анализа проблемы пользователя."""

    category_code: str
    title: str
    responsible: str
    urgency: str
    is_ready: bool
    question: str | None = None
    draft: str | None = None
    explanation: str = ""
    missing_fields: list[str] = field(default_factory=list)


class AIService(Protocol):
    """Контракт AI-слоя."""

    async def analyze(
        self,
        turns: list[DialogTurn],
        category_code: str | None = None,
    ) -> Analysis:
        """Разбирает диалог и решает: спросить ещё или сформировать текст."""
        ...

    async def refine(self, draft: str, comment: str) -> str:
        """Правит готовый текст обращения по замечанию пользователя."""
        ...
