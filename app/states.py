"""FSM-состояния диалога создания обращения."""

from __future__ import annotations

from maxapi.context import State, StatesGroup


class CreateRequest(StatesGroup):
    """Состояния сценария «проблема → обращение»."""

    #: Бот ждёт описание проблемы или ответ на уточняющий вопрос.
    collecting = State()
    #: Показан черновик обращения, пользователь может его править текстом.
    editing_draft = State()
