"""Промпты и сборка диалога в формат чата.

Один и тот же модуль используется при обучении и в рантайме —
это гарантирует, что модель видит на инференсе ровно тот формат,
на котором её учили.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from domain.tickets.catalog import CATEGORIES, OTHER
from infrastructure.llm.schemas import SLOT_TITLES, required_slots

Role = Literal["system", "user", "assistant"]
ChatMessage = dict[str, str]

#: Типы задач, которым учим модель.
TASK_DIALOG = "dialog"
TASK_REFINE = "refine"


def _categories_block() -> str:
    """Перечень категорий для системного промпта."""

    lines = [
        f"- {category.code}: {category.title} (ответственный: {category.responsible})"
        for category in (*CATEGORIES, OTHER)
    ]
    return "\n".join(lines)


def _slots_block() -> str:
    """Перечень слотов для системного промпта."""

    return "\n".join(f"- {name}: {title}" for name, title in SLOT_TITLES.items())


SYSTEM_PROMPT = f"""Ты — помощник жителя многоквартирного дома в России.
Житель описывает бытовую проблему своими словами. Твоя работа —
довести её до корректного обращения в управляющую организацию.

На каждом шаге ты делаешь ровно одно из двух:
1. action="ask" — задаёшь ОДИН короткий уточняющий вопрос, если без
   ответа на него обращение нельзя оформить или передать исполнителю;
2. action="draft" — формируешь готовый текст обращения, когда данных
   достаточно.

Категории проблем:
{_categories_block()}

Слоты, которые нужно собрать:
{_slots_block()}

Правила:
- задавай только те вопросы, которые реально влияют на действия УК;
- один вопрос за раз, на языке жителя, без канцелярита и без списков;
- не выдумывай факты: в slots попадает только то, что сказал житель;
- не ссылайся на нормативные документы и сроки, если их не назвал
  житель, — домыслы недопустимы;
- если признаков аварии нет, не завышай срочность;
- срочность "аварийная" — только при угрозе людям или имуществу
  (сильная течь, запах газа, застрявший в лифте человек, нет
  отопления зимой);
- текст обращения пиши от первого лица, вежливо и по делу:
  суть, место, время, просьба устранить и сообщить о результате;
- отвечай ТОЛЬКО одним JSON-объектом, без пояснений и markdown.

Формат ответа:
{{"action": "ask"|"draft", "category": "<код>", "urgency": "<низкая|обычная|высокая|аварийная>",
 "slots": {{"problem": str|null, "location": str|null, "started_at": str|null,
 "severity": str|null, "access": str|null}}, "missing_slots": [<коды слотов>],
 "question": str|null, "draft": str|null, "explanation": str}}"""


def build_dialog_messages(
    turns: list[dict[str, str]],
    category_hint: str | None = None,
) -> list[ChatMessage]:
    """Собирает чат для задачи «следующий шаг диалога».

    Args:
        turns: реплики вида {"role": "user"|"bot", "text": ...}.
        category_hint: категория, выбранная кнопкой, если житель её выбрал.
    """

    messages: list[ChatMessage] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if category_hint:
        messages.append(
            {
                "role": "user",
                "content": (
                    f"[житель выбрал быстрый сценарий: {category_hint}; "
                    f"обязательные слоты: "
                    f"{', '.join(required_slots(category_hint))}]"
                ),
            }
        )

    for turn in turns:
        role: Role = "user" if turn.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": turn.get("text", "")})

    return messages


def build_refine_messages(
    draft: str, comment: str, category_hint: str | None = None
) -> list[ChatMessage]:
    """Собирает чат для задачи «поправить готовый текст обращения»."""

    hint = f"\nКатегория: {category_hint}" if category_hint else ""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Ниже готовый текст обращения и замечание жителя. "
                "Перепиши текст с учётом замечания, сохранив факты и "
                'структуру. Верни JSON с action="draft".'
                f"{hint}\n\n"
                f"Текст обращения:\n{draft}\n\n"
                f"Замечание жителя: {comment}"
            ),
        },
    ]


def build_messages(
    task: str,
    payload: dict[str, Any],
) -> list[ChatMessage]:
    """Единая точка сборки чата по типу задачи."""

    if task == TASK_DIALOG:
        return build_dialog_messages(
            payload.get("turns", []), payload.get("category_hint")
        )

    if task == TASK_REFINE:
        return build_refine_messages(
            payload["draft"],
            payload["comment"],
            payload.get("category_hint"),
        )

    raise ValueError(f"Неизвестный тип задачи: {task}")


def extract_json(raw: str) -> dict[str, Any]:
    """Достаёт JSON-объект из ответа модели.

    Модель обучена отвечать чистым JSON, но на инференсе (особенно до
    дообучения) встречаются обёртки ```json и болтовня вокруг — этот
    разбор делает пайплайн устойчивым.
    """

    text = raw.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("В ответе модели нет JSON-объекта")

    return json.loads(text[start : end + 1])
