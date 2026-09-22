"""Генератор синтетических диалогов для стартовой выборки.

Это bootstrap-данные: они задают формат, покрывают все категории и
слоты и позволяют получить первую дообученную версию модели.
Перед финальным обучением их обязательно нужно разбавить реальными
и вручную проверенными диалогами — синтетика одна даёт шаблонные
формулировки и не покрывает «кривые» сообщения жителей.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from infrastructure.llm.prompts import (
    TASK_DIALOG,
    TASK_REFINE,
    build_dialog_messages,
    build_refine_messages,
)
from ml.dataset.schema import TrainingExample
from infrastructure.llm.schemas import ModelDecision, Slots, required_slots


@dataclass(frozen=True)
class CategorySeed:
    """Заготовки формулировок для одной категории."""

    code: str
    responsible: str
    openings: tuple[str, ...]
    locations: tuple[str, ...]
    severities: tuple[str, ...]
    emergency_markers: tuple[str, ...]
    summary: str


SEEDS: tuple[CategorySeed, ...] = (
    CategorySeed(
        code="water",
        responsible="управляющая организация (аварийная служба)",
        openings=(
            "Течёт труба",
            "В ванной капает с потолка",
            "Затопило коридор",
            "Возле стояка всё мокро",
            "Прорвало трубу в подвале",
        ),
        locations=(
            "подъезд 2, 5 этаж",
            "квартира 43, ванная",
            "подвал под первым подъездом",
            "лестничная клетка, 3 этаж",
        ),
        severities=(
            "капает несильно",
            "течёт струёй, вода на полу",
            "вода льётся, заливает соседей снизу",
        ),
        emergency_markers=("льётся", "заливает", "прорвало", "хлещет"),
        summary="протечка воды",
    ),
    CategorySeed(
        code="light",
        responsible="управляющая организация (электрик)",
        openings=(
            "Нет света на лестничной клетке",
            "Не горят лампы в подъезде",
            "Выбивает автомат в щитке",
            "Пропал свет на этаже",
        ),
        locations=(
            "подъезд 1, 4 этаж",
            "подъезд 3, все этажи",
            "площадка у квартиры 12",
            "тамбур на первом этаже",
        ),
        severities=(
            "темно, но розетки работают",
            "света нет совсем, вечером не пройти",
            "искрит щиток, пахнет горелым",
        ),
        emergency_markers=("искрит", "пахнет горелым", "дым"),
        summary="отсутствие освещения",
    ),
    CategorySeed(
        code="heating",
        responsible="управляющая организация (теплоснабжение)",
        openings=(
            "Холодные батареи",
            "В квартире холодно",
            "Не греет отопление",
            "Одна батарея еле тёплая",
        ),
        locations=(
            "квартира 78, обе комнаты",
            "квартира 12, кухня",
            "подъезд 4, 9 этаж",
        ),
        severities=(
            "батареи чуть тёплые",
            "батареи ледяные, дома 14 градусов",
            "отопления нет второй день, в квартире ребёнок",
        ),
        emergency_markers=("ледяные", "нет второй день", "14 градусов"),
        summary="проблема с отоплением",
    ),
    CategorySeed(
        code="door",
        responsible="управляющая организация (обслуживание МОП)",
        openings=(
            "Не закрывается дверь подъезда",
            "Глючит домофон",
            "Сломался доводчик",
            "Не открывается дверь по ключу",
        ),
        locations=("подъезд 2", "подъезд 5", "подъезд 1, вход со двора"),
        severities=(
            "дверь просто не защёлкивается",
            "дверь стоит нараспашку, заходят посторонние",
            "домофон не открывает, приходится ждать соседей",
        ),
        emergency_markers=("нараспашку", "посторонние"),
        summary="неисправность двери или домофона",
    ),
    CategorySeed(
        code="cleaning",
        responsible="управляющая организация (санитарное содержание)",
        openings=(
            "Не убирают подъезд",
            "Мусор возле контейнеров не вывозят",
            "Грязь на лестнице",
            "Завален мусоропровод",
        ),
        locations=(
            "подъезд 3, этажи с 1 по 5",
            "контейнерная площадка у дома",
            "подъезд 2, первый этаж",
        ),
        severities=(
            "пыльно и не мыли пол",
            "мусор лежит неделю, появился запах",
            "не пройти, пакеты стоят на площадке",
        ),
        emergency_markers=("запах", "крысы", "не пройти"),
        summary="нарушение санитарного содержания",
    ),
    CategorySeed(
        code="lift",
        responsible="управляющая организация (лифтовая служба)",
        openings=(
            "Не работает лифт",
            "Лифт застревает между этажами",
            "Двери лифта не открываются",
            "Лифт дёргается при движении",
        ),
        locations=("подъезд 4", "подъезд 1, пассажирский лифт", "подъезд 6"),
        severities=(
            "лифт просто стоит на первом этаже",
            "лифт встал между этажами, внутри человек",
            "двери закрываются рывками, страшно заходить",
        ),
        emergency_markers=("внутри человек", "застрял", "между этажами"),
        summary="неисправность лифта",
    ),
)

STARTED_AT = (
    "сегодня утром",
    "вчера вечером",
    "второй день",
    "с прошлой недели",
    "примерно час назад",
)

ACCESS = (
    "я дома весь день, квартира 43",
    "можно позвонить мне на телефон, открою",
    "доступ свободный, это общий коридор",
)

#: Вопросы, которыми модель добирает недостающие слоты.
SLOT_QUESTIONS: dict[str, tuple[str, ...]] = {
    "location": (
        "Подскажите, где именно это происходит — подъезд, этаж, квартира?",
        "Уточните адрес внутри дома: какой подъезд и этаж?",
    ),
    "started_at": (
        "Когда это началось?",
        "Как давно так происходит?",
    ),
    "severity": (
        "Насколько всё серьёзно сейчас?",
        "Опишите, насколько сильно — есть ли угроза людям или имуществу?",
    ),
    "access": (
        "Как мастеру попасть на место — вы будете дома?",
        "Кому позвонить для доступа на место?",
    ),
    "problem": (
        "Опишите, пожалуйста, что именно происходит.",
        "Что конкретно случилось?",
    ),
}

REFINE_COMMENTS = (
    ("добавь, что в квартире маленький ребёнок", "в квартире маленький ребёнок"),
    ("укажи, что я прошу позвонить заранее", "прошу позвонить заранее"),
    ("напиши, что это повторяется третий раз", "проблема повторяется третий раз"),
    ("добавь номер квартиры 43", "квартира 43"),
    ("укажи, что нужен ответ в письменном виде", "прошу письменный ответ"),
)


def _urgency(seed: CategorySeed, severity: str) -> str:
    """Срочность по описанию серьёзности проблемы."""

    if any(marker in severity for marker in seed.emergency_markers):
        return "аварийная"
    if seed.code in {"water", "heating", "light", "lift"}:
        return "высокая"
    return "обычная"


def _draft_text(seed: CategorySeed, slots: Slots) -> str:
    """Эталонный текст обращения — целевой стиль модели."""

    lines = [
        f"Прошу устранить {seed.summary}.",
        "",
        f"Что произошло: {slots.problem}.",
        f"Где: {slots.location}.",
        f"Когда началось: {slots.started_at}.",
    ]
    if slots.severity:
        lines.append(f"Сейчас ситуация такая: {slots.severity}.")
    if slots.access:
        lines.append(f"Доступ на место: {slots.access}.")
    lines += [
        "",
        "Прошу зарегистрировать обращение, направить специалиста, "
        "сообщить срок устранения и уведомить меня о результате.",
    ]
    return "\n".join(lines)


def _explanation(seed: CategorySeed, urgency: str) -> str:
    """Короткое объяснение «кто отвечает и что дальше»."""

    return (
        f"Ответственный: {seed.responsible}. Срочность: {urgency}. "
        "После отправки обращение получит номер и статус."
    )


def _dialog_examples(
    rng: random.Random, seed: CategorySeed
) -> list[TrainingExample]:
    """Один диалог: несколько шагов «спросить» и финальный «черновик»."""

    needed = list(required_slots(seed.code))
    severity = rng.choice(seed.severities)
    values = {
        "problem": f"{rng.choice(seed.openings).lower()}",
        "location": rng.choice(seed.locations),
        "started_at": rng.choice(STARTED_AT),
        "severity": severity,
        "access": rng.choice(ACCESS),
    }
    urgency = _urgency(seed, severity)

    # Сколько слотов житель назвал сразу — от этого зависит длина диалога.
    known = ["problem"]
    extra_known = rng.sample(
        [s for s in needed if s != "problem"],
        k=rng.randint(0, max(0, len(needed) - 2)),
    )
    known += extra_known

    opening = values["problem"]
    for slot in extra_known:
        opening += f", {values[slot]}"

    turns: list[dict[str, str]] = [{"role": "user", "text": opening}]
    slots = Slots(**{slot: values[slot] for slot in known})
    examples: list[TrainingExample] = []
    category_hint = seed.code if rng.random() < 0.5 else None

    while True:
        missing = slots.missing(seed.code)
        messages = build_dialog_messages(turns, category_hint)

        if missing:
            slot = missing[0]
            question = rng.choice(SLOT_QUESTIONS[slot])
            decision = ModelDecision(
                action="ask",
                category=seed.code,
                urgency=urgency,
                slots=slots.model_copy(deep=True),
                missing_slots=missing,
                question=question,
                explanation=_explanation(seed, urgency),
            )
            examples.append(
                TrainingExample.build(
                    TASK_DIALOG,
                    messages,
                    decision,
                    category=seed.code,
                    step="ask",
                    slot=slot,
                )
            )

            turns.append({"role": "bot", "text": question})
            turns.append({"role": "user", "text": values[slot]})
            slots = slots.model_copy(update={slot: values[slot]})
            continue

        decision = ModelDecision(
            action="draft",
            category=seed.code,
            urgency=urgency,
            slots=slots,
            missing_slots=[],
            draft=_draft_text(seed, slots),
            explanation=_explanation(seed, urgency),
        )
        examples.append(
            TrainingExample.build(
                TASK_DIALOG,
                messages,
                decision,
                category=seed.code,
                step="draft",
            )
        )
        break

    examples.append(_refine_example(rng, seed, slots, urgency))
    return examples


def _refine_example(
    rng: random.Random, seed: CategorySeed, slots: Slots, urgency: str
) -> TrainingExample:
    """Пример правки готового текста по замечанию жителя."""

    comment, addition = rng.choice(REFINE_COMMENTS)
    draft = _draft_text(seed, slots)
    updated = draft.replace(
        "Прошу зарегистрировать обращение",
        f"Дополнительно: {addition}.\n\nПрошу зарегистрировать обращение",
    )

    decision = ModelDecision(
        action="draft",
        category=seed.code,
        urgency=urgency,
        slots=slots,
        missing_slots=[],
        draft=updated,
        explanation=_explanation(seed, urgency),
    )
    return TrainingExample.build(
        TASK_REFINE,
        build_refine_messages(draft, comment, seed.code),
        decision,
        category=seed.code,
        step="refine",
    )


def generate(count: int, seed_value: int = 42) -> list[TrainingExample]:
    """Генерирует примерно `count` примеров, детерминированно по seed."""

    rng = random.Random(seed_value)
    examples: list[TrainingExample] = []

    while len(examples) < count:
        category_seed = rng.choice(SEEDS)
        examples.extend(_dialog_examples(rng, category_seed))

    return examples[:count]
