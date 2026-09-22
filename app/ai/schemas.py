"""Структуры данных AI-слоя.

AI обязан возвращать валидируемый структурированный результат,
а не свободный текст: на его основе строится вся дальнейшая логика.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

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
