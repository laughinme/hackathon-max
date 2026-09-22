"""Сценарий «проблема → обращение в УК».

Путь пользователя:
быстрый сценарий или свободный текст → уточнения от AI →
черновик обращения → правка текстом → «Готово» → заявка со статусом.
"""

from __future__ import annotations

import logging

from maxapi import Router
from maxapi.context import MemoryContext
from maxapi.types.updates import MessageCallback, MessageCreated

from app import callbacks, keyboards, texts
from app.ai.schemas import Analysis, DialogTurn
from app.categories import get_category
from app.models import Request, RequestStatus
from app.notifier import schedule_demo_status_flow
from app.screen import render, user_message_text
from app.services import get_services
from app.states import CreateRequest

logger = logging.getLogger(__name__)
router = Router(router_id="create")

# Ключи FSM-контекста сценария.
TURNS = "turns"
CATEGORY = "category"
DRAFT = "draft"
RESPONSIBLE = "responsible"
URGENCY = "urgency"
TITLE = "title"
REQUEST_ID = "request_id"


@router.message_callback(callbacks.is_action(callbacks.NEW))
async def on_new_request(
    event: MessageCallback, context: MemoryContext
) -> None:
    """Экран быстрых сценариев."""

    await _reset_scenario(context)
    await render(
        event, context, texts.choose_category(), keyboards.categories_menu()
    )


@router.message_callback(callbacks.has_action(callbacks.CATEGORY))
async def on_category(
    event: MessageCallback, context: MemoryContext
) -> None:
    """Выбран быстрый сценарий — переходим к уточнениям."""

    _, code = callbacks.unpack(event.callback.payload)
    category = get_category(code)

    await _reset_scenario(context)
    await context.update_data(
        **{
            CATEGORY: category.code,
            TURNS: [
                {"role": "user", "text": f"Проблема: {category.title}"}
            ],
        }
    )
    await context.set_state(CreateRequest.collecting)

    await render(
        event,
        context,
        texts.collecting_started(
            category.title, category.clarifying_question
        ),
        keyboards.collecting(),
    )


@router.message_created(CreateRequest.collecting)
async def on_collecting_message(
    event: MessageCreated, context: MemoryContext
) -> None:
    """Ответ пользователя на уточняющий вопрос."""

    text = user_message_text(event)
    if not text:
        return

    await _append_turn(context, "user", text)
    await _analyze_and_render(event, context)


@router.message_created(CreateRequest.editing_draft)
async def on_draft_comment(
    event: MessageCreated, context: MemoryContext
) -> None:
    """Пользователь пишет, что поправить в черновике."""

    comment = user_message_text(event)
    if not comment:
        return

    services = get_services()
    data = await context.get_data()
    draft = data.get(DRAFT, "")

    updated = await services.ai.refine(draft, comment)
    await context.update_data(**{DRAFT: updated})

    await render(
        event,
        context,
        texts.draft(
            updated,
            data.get(RESPONSIBLE, "Управляющая организация"),
            data.get(URGENCY, "обычная"),
        ),
        keyboards.draft(),
    )


@router.message_callback(callbacks.is_action(callbacks.DRAFT_RESTART))
async def on_restart(
    event: MessageCallback, context: MemoryContext
) -> None:
    """Начать оформление заново."""

    await _reset_scenario(context)
    await render(
        event,
        context,
        texts.choose_category(),
        keyboards.categories_menu(),
        notification="Начинаем заново",
    )


@router.message_callback(callbacks.is_action(callbacks.DRAFT_DONE))
async def on_submit(event: MessageCallback, context: MemoryContext) -> None:
    """«Готово» — регистрируем обращение и отправляем его в УК."""

    services = get_services()
    data = await context.get_data()
    draft = data.get(DRAFT)

    if not draft:
        await render(
            event,
            context,
            texts.choose_category(),
            keyboards.categories_menu(),
            notification="Черновик не найден, начнём заново",
        )
        return

    await render(event, context, texts.submitting(), keyboards.draft())

    request = await _get_or_create_request(event, context, data, draft)
    result = await services.uk.submit(request)

    if not result.ok:
        await render(
            event,
            context,
            texts.submit_failed(result.error or "неизвестная ошибка"),
            keyboards.retry_submit(),
        )
        return

    request.external_id = result.external_id
    request.is_mock_integration = result.is_mock
    request.set_status(RequestStatus.SENT)

    await _reset_scenario(context)
    await context.set_state(None)

    await render(
        event,
        context,
        texts.submitted(request),
        keyboards.after_submit(),
        notification=f"Обращение {request.number} отправлено",
    )

    if services.config.demo_status_simulation and event.bot is not None:
        schedule_demo_status_flow(
            event.bot, request, services.config.demo_status_delay_sec
        )


async def _analyze_and_render(
    event: MessageCreated, context: MemoryContext
) -> None:
    """Прогоняет диалог через AI и показывает вопрос либо черновик."""

    services = get_services()
    data = await context.get_data()
    turns = [DialogTurn(**turn) for turn in data.get(TURNS, [])]

    analysis: Analysis = await services.ai.analyze(
        turns, category_code=data.get(CATEGORY)
    )

    if not analysis.is_ready or not analysis.draft:
        question = analysis.question or "Расскажите, пожалуйста, подробнее."
        await _append_turn(context, "bot", question)
        await render(
            event,
            context,
            texts.clarifying(question, analysis.explanation),
            keyboards.collecting(),
        )
        return

    await context.update_data(
        **{
            DRAFT: analysis.draft,
            CATEGORY: analysis.category_code,
            TITLE: analysis.title,
            RESPONSIBLE: analysis.responsible,
            URGENCY: analysis.urgency,
        }
    )
    await context.set_state(CreateRequest.editing_draft)

    await render(
        event,
        context,
        texts.draft(
            analysis.draft, analysis.responsible, analysis.urgency
        ),
        keyboards.draft(),
    )


async def _get_or_create_request(
    event: MessageCallback,
    context: MemoryContext,
    data: dict,
    draft: str,
) -> Request:
    """Возвращает заявку сценария, создавая её при первой отправке.

    Нужно для повторной отправки после ошибки: дубликат не создаётся.
    """

    services = get_services()
    request_id = data.get(REQUEST_ID)

    if request_id:
        existing = await services.requests.get(request_id)
        if existing is not None:
            existing.text = draft
            return existing

    chat_id, user_id = event.get_ids()
    category = get_category(data.get(CATEGORY))

    request = await services.requests.create(
        user_id=user_id,
        chat_id=chat_id,
        title=data.get(TITLE) or category.title,
        category=category.code,
        text=draft,
        responsible=data.get(RESPONSIBLE) or category.responsible,
        urgency=data.get(URGENCY) or category.urgency,
    )
    await context.update_data(**{REQUEST_ID: request.id})
    return request


async def _append_turn(
    context: MemoryContext, role: str, text: str
) -> None:
    """Добавляет реплику в диалог уточнения."""

    data = await context.get_data()
    turns = list(data.get(TURNS, []))
    turns.append({"role": role, "text": text})
    await context.update_data(**{TURNS: turns})


async def _reset_scenario(context: MemoryContext) -> None:
    """Очищает данные и состояние сценария, сохраняя привязку к экрану."""

    await context.set_state(None)
    await context.update_data(
        **{
            TURNS: [],
            CATEGORY: None,
            DRAFT: None,
            TITLE: None,
            RESPONSIBLE: None,
            URGENCY: None,
            REQUEST_ID: None,
        }
    )
