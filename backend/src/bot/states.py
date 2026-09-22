"""FSM-состояния диалога создания обращения."""

from __future__ import annotations

from maxapi.context import State, StatesGroup


class CreateRequest(StatesGroup):
    """Состояния сценария «проблема → обращение»."""

    #: Бот ждёт описание проблемы или ответ на уточняющий вопрос.
    collecting = State()
    #: Классификатор не уверен в аварийности: ждём ответа кнопкой.
    confirming_emergency = State()
    #: Показан черновик обращения, пользователь может его править текстом.
    editing_draft = State()


class DispatcherFlow(StatesGroup):
    """Dispatcher changes a status and may add a comment for the resident."""

    #: Waiting for an optional comment before applying the status change.
    commenting = State()
