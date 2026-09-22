"""Справочник типовых проблем.

Быстрые кнопки — это ярлыки, а не обязательный каталог: пользователь
всегда может описать проблему своими словами, тогда категорию
определяет AI-слой.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    """Типовая проблема жителя МКД."""

    code: str
    emoji: str
    title: str
    responsible: str
    urgency: str
    clarifying_question: str
    keywords: tuple[str, ...]

    @property
    def button_text(self) -> str:
        return f"{self.emoji} {self.title}"


CATEGORIES: tuple[Category, ...] = (
    Category(
        code="water",
        emoji="💧",
        title="Вода / протечка",
        responsible="Управляющая организация (аварийная служба)",
        urgency="высокая",
        clarifying_question=(
            "Где именно течёт и насколько сильно — капает, течёт струёй "
            "или уже стоит вода? Укажите этаж и квартиру/подъезд."
        ),
        keywords=("вода", "теч", "протеч", "залив", "труб", "кран", "сыро"),
    ),
    Category(
        code="light",
        emoji="💡",
        title="Нет света",
        responsible="Управляющая организация (электрик)",
        urgency="высокая",
        clarifying_question=(
            "Света нет во всей квартире, в подъезде или на этаже? "
            "Укажите подъезд и этаж, и когда это началось."
        ),
        keywords=("свет", "электр", "лампоч", "розетк", "щиток", "темно"),
    ),
    Category(
        code="heating",
        emoji="🔥",
        title="Отопление",
        responsible="Управляющая организация (теплоснабжение)",
        urgency="высокая",
        clarifying_question=(
            "Батареи холодные во всей квартире или только часть? "
            "Укажите этаж, квартиру и примерную температуру в комнате."
        ),
        keywords=("отоплен", "батаре", "холодно", "тепло", "радиатор"),
    ),
    Category(
        code="door",
        emoji="🚪",
        title="Дверь / домофон",
        responsible="Управляющая организация (обслуживание МОП)",
        urgency="обычная",
        clarifying_question=(
            "В каком подъезде проблема и что именно не работает — "
            "дверь не закрывается, не открывается или сломан домофон?"
        ),
        keywords=("дверь", "домофон", "подъезд", "замок", "ключ", "магнит"),
    ),
    Category(
        code="cleaning",
        emoji="🗑",
        title="Уборка / мусор",
        responsible="Управляющая организация (санитарное содержание)",
        urgency="обычная",
        clarifying_question=(
            "Где именно проблема — подъезд, площадка, контейнерная "
            "площадка? Укажите подъезд/этаж и как давно так."
        ),
        keywords=("мусор", "убор", "грязн", "контейнер", "свалк", "запах"),
    ),
    Category(
        code="lift",
        emoji="🛗",
        title="Лифт",
        responsible="Управляющая организация (лифтовая служба)",
        urgency="высокая",
        clarifying_question=(
            "Что с лифтом — не работает, застревает, не открываются "
            "двери? В каком подъезде и есть ли кто-то внутри?"
        ),
        keywords=("лифт", "кабин"),
    ),
)

OTHER = Category(
    code="other",
    emoji="✍️",
    title="Другая проблема",
    responsible="Управляющая организация",
    urgency="обычная",
    clarifying_question=(
        "Уточните, пожалуйста, где именно это происходит "
        "(подъезд, этаж, квартира) и как давно."
    ),
    keywords=(),
)

_BY_CODE: dict[str, Category] = {c.code: c for c in (*CATEGORIES, OTHER)}


def get_category(code: str | None) -> Category:
    """Категория по коду; для неизвестного кода — «Другая проблема»."""

    if not code:
        return OTHER
    return _BY_CODE.get(code, OTHER)


def guess_category(text: str) -> Category:
    """Грубое определение категории по ключевым словам.

    Это резервный путь для MVP. В боевой версии категорию определяет
    LLM-классификатор (см. app/ai/service.py).
    """

    lowered = text.lower()
    best: Category | None = None
    best_score = 0

    for category in CATEGORIES:
        score = sum(1 for kw in category.keywords if kw in lowered)
        if score > best_score:
            best, best_score = category, score

    return best or OTHER
