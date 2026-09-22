"""Формат обучающего примера.

Один пример — это чат (system + история диалога) и целевой JSON,
который модель должна выдать следующим сообщением ассистента.
Хранится в JSONL: по одному объекту на строку.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

from infrastructure.llm.prompts import ChatMessage
from infrastructure.llm.schemas import ModelDecision


@dataclass
class TrainingExample:
    """Обучающий пример для SFT."""

    task: str
    messages: list[ChatMessage]
    target: str
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        task: str,
        messages: list[ChatMessage],
        decision: ModelDecision,
        **meta: Any,
    ) -> TrainingExample:
        """Собирает пример из решения модели."""

        return cls(
            task=task,
            messages=messages,
            target=decision.as_training_target(),
            meta=meta,
        )

    def to_chat(self) -> list[ChatMessage]:
        """Полный чат вместе с ответом ассистента — формат для SFT."""

        return [*self.messages, {"role": "assistant", "content": self.target}]

    def validate(self) -> ModelDecision:
        """Проверяет, что целевой JSON соответствует контракту."""

        return ModelDecision.model_validate_json(self.target)


def write_jsonl(path: Path, examples: Iterable[TrainingExample]) -> int:
    """Пишет примеры в JSONL, возвращает количество записанных."""

    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with path.open("w", encoding="utf-8") as handle:
        for example in examples:
            example.validate()
            handle.write(
                json.dumps(asdict(example), ensure_ascii=False) + "\n"
            )
            count += 1

    return count


def read_jsonl(path: Path) -> Iterator[TrainingExample]:
    """Читает примеры из JSONL."""

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield TrainingExample(**json.loads(line))
