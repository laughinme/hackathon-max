"""Does a chat message complain about something, or is it small talk?

A classifier always picks some category: "кто потерял ключи?" looks like
"door". In a house chat the bot must stay silent on such messages, so a
category alone is not enough; the text also has to say that something is
wrong. The list is short on purpose and errs towards silence: a neighbour who
is not noticed can still file through the bot, a bot that nags gets kicked.
"""

from __future__ import annotations

import re

PROBLEM_MARKERS: tuple[str, ...] = (
    "не работа",
    "не гор",
    "не откры",
    "не закры",
    "не убира",
    "не вывоз",
    "не греет",
    "нет воды",
    "нет света",
    "нет тепла",
    "нет отоплен",
    "нет горяч",
    "сломал",
    "слома",
    "теч",
    "тёч",
    "протек",
    "протёк",
    "затоп",
    "залива",
    "капает",
    "застр",
    "грязн",
    "воня",
    "запах",
    "темно",
    "холодн",
    "авари",
    "разбит",
    "искрит",
    "плесен",
    "отключ",
    "опять",
    "снова",
    "который день",
    "уже неделю",
    "уже день",
)


def sounds_like_complaint(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower())
    return any(marker in normalized for marker in PROBLEM_MARKERS)
