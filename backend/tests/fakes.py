"""Test doubles shared by unit and integration tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from application.ports.classifier import Classification


class FixedClock:
    def __init__(self, now: datetime | None = None) -> None:
        self.current = now or datetime(2026, 9, 23, 9, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class StaticClassifier:
    def __init__(self, classification: Classification) -> None:
        self.classification = classification
        self.texts: list[str] = []

    async def classify(self, text: str) -> Classification:
        self.texts.append(text)
        return self.classification


def classification(
    category: str = "lift",
    *,
    is_emergency: bool = False,
    emergency_confidence: float = 0.9,
) -> Classification:
    return Classification(
        category_code=category,
        category_confidence=0.9,
        is_emergency=is_emergency,
        emergency_confidence=emergency_confidence,
    )
