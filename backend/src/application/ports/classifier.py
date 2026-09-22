"""Контракт классификатора жалоб: категория и аварийность.

Оба выхода — прямой вход в будущий SlaPolicy (DECISIONS D-005):
категория без аварийности не даёт правильный нормативный срок, и
наоборот («лифт не работает» — сутки, «лифт застрял, там человек» —
30 минут). Поэтому это один порт с двумя выходами, а не отдельная
модель «приоритета для сортировки» — сортировка очереди диспетчера
считается по остатку времени до срока и ML не требует.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Classification:
    """Результат классификации одной жалобы."""

    category_code: str
    category_confidence: float
    is_emergency: bool
    emergency_confidence: float


class Classifier(Protocol):
    """Классифицирует текст жалобы: категория + аварийность."""

    async def classify(self, text: str) -> Classification:
        """Определяет категорию и аварийность по тексту жалобы."""
        ...
