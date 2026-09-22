"""Реализация порта AIService на правилах (без LLM).

⚠️ Это ЗАГЛУШКА (`StubAIService`) — детерминированная логика
на правилах. Она полностью повторяет контракт будущей LLM-реализации,
поэтому LLM подключается через тот же порт в `app/services.py`.
"""

from __future__ import annotations

import logging

from application.ports.ai import Analysis, DialogTurn
from domain.tickets.catalog import Category, get_category, guess_category

logger = logging.getLogger(__name__)

#: Сколько реплик пользователя собираем до генерации обращения.
MIN_USER_TURNS = 2


class StubAIService:
    """Заглушка AI. Заменяется на LLM без изменения хендлеров."""

    async def analyze(
        self,
        turns: list[DialogTurn],
        category_code: str | None = None,
    ) -> Analysis:
        user_texts = [t.text for t in turns if t.role == "user"]
        joined = " ".join(user_texts).strip()

        category = (
            get_category(category_code) if category_code else guess_category(joined)
        )

        # Данных мало — задаём один уточняющий вопрос и ждём ответ.
        if len(user_texts) < MIN_USER_TURNS:
            return Analysis(
                category_code=category.code,
                title=category.title,
                responsible=category.responsible,
                urgency=category.urgency,
                is_ready=False,
                question=category.clarifying_question,
                missing_fields=["location", "details"],
                explanation=(
                    f"Похоже на категорию «{category.title}». "
                    f"Предполагаемый ответственный: {category.responsible}."
                ),
            )

        return Analysis(
            category_code=category.code,
            title=category.title,
            responsible=category.responsible,
            urgency=category.urgency,
            is_ready=True,
            draft=self._build_draft(category, user_texts),
            explanation=(
                f"Ответственный: {category.responsible}. "
                "После отправки обращение получит номер и статус, "
                "изменения придут уведомлением в этот чат."
            ),
        )

    async def refine(self, draft: str, comment: str) -> str:
        """Заглушка редактирования: дописывает уточнение пользователя."""

        marker = "Уточнение от заявителя:"
        base = draft.split(marker)[0].rstrip()
        return f"{base}\n\n{marker} {comment.strip()}"

    @staticmethod
    def _build_draft(category: Category, user_texts: list[str]) -> str:
        """Собирает текст обращения из реплик пользователя."""

        description = user_texts[0].strip()
        details = " ".join(t.strip() for t in user_texts[1:]).strip()

        lines = [
            "Прошу принять обращение и устранить проблему.",
            "",
            f"Категория: {category.title}",
            f"Суть обращения: {description}",
        ]
        if details:
            lines.append(f"Детали: {details}")
        lines += [
            f"Срочность: {category.urgency}",
            "",
            "Прошу зарегистрировать обращение, сообщить срок "
            "устранения и уведомить о результате.",
        ]
        return "\n".join(lines)
