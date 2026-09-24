"""Scenario "problem -> registered ticket with a legal deadline".

Quick category or free text -> AI clarifying question -> triage (category,
emergency, deadline) -> emergency confirmation if the classifier is unsure ->
draft -> edits by message -> "Send" -> ticket with number and deadline.
"""

from __future__ import annotations

import logging
from uuid import UUID

from maxapi import Router
from maxapi.context.base import BaseContext
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated

from app.services import Services
from application.ports.ai import Analysis, DialogTurn
from application.tickets.create_ticket import CreateTicketCommand
from application.tickets.dto import TicketView
from application.tickets.triage_complaint import TriageResult
from bot import callbacks, keyboards, media, texts
from bot.scopes import DialogScope
from bot.screen import render, sender_id, user_message_text
from bot.states import CreateRequest
from bot.views import show_building_choice
from domain.housing.exceptions import ResidentNotBoundError
from domain.tickets.catalog import get_category
from domain.tickets.entities import MAX_PHOTOS

logger = logging.getLogger(__name__)
router = Router(router_id="create")
router.filter(DialogScope())

# FSM context keys of the scenario.
TURNS = "turns"
CATEGORY = "category"
DRAFT = "draft"
IS_EMERGENCY = "is_emergency"
TICKET_ID = "ticket_id"
PHOTOS = "photos"
SCENARIO_KEYS = (TURNS, CATEGORY, DRAFT, IS_EMERGENCY, TICKET_ID, PHOTOS)


@router.message_callback(callbacks.is_action(callbacks.NEW))
async def on_new_request(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    await reset_scenario(context)
    user_id = sender_id(event)
    identity = await services.identify.execute(user_id)
    if identity.residency is None:
        await show_building_choice(event, context, services, pending_problem=False)
        return
    await render(event, context, texts.choose_category(), keyboards.categories_menu())


@router.message_callback(callbacks.has_action(callbacks.CATEGORY))
async def on_category(event: MessageCallback, context: BaseContext) -> None:
    _, code = callbacks.unpack(event.callback.payload)
    category = get_category(code)

    await reset_scenario(context)
    await context.update_data(
        **{
            CATEGORY: category.code,
            TURNS: [{"role": "user", "text": f"Проблема: {category.title}"}],
        }
    )
    await context.set_state(CreateRequest.collecting)
    await render(
        event,
        context,
        texts.collecting_started(category.title, category.clarifying_question),
        keyboards.collecting(),
    )


@router.message_created(CreateRequest.collecting)
async def on_collecting_message(
    event: MessageCreated, context: BaseContext, services: Services
) -> None:
    text = user_message_text(event)
    photos = await remember_photos(event, context)
    if not text:
        if photos:
            await render(
                event, context, texts.photo_added(photos), keyboards.collecting()
            )
        return
    await append_turn(context, "user", text)
    await analyze_and_render(event, context, services)


@router.message_callback(
    CreateRequest.confirming_emergency, callbacks.has_action(callbacks.EMERGENCY)
)
async def on_emergency_answer(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    _, answer = callbacks.unpack(event.callback.payload)
    is_emergency = answer == "yes"
    data = await context.get_data()

    await context.update_data(**{IS_EMERGENCY: is_emergency})
    await context.set_state(CreateRequest.editing_draft)
    triage = services.triage.preview(data[CATEGORY], is_emergency)
    await render(
        event,
        context,
        texts.draft(data[DRAFT], triage, len(data.get(PHOTOS) or [])),
        keyboards.draft(),
    )


@router.message_created(CreateRequest.editing_draft)
async def on_draft_comment(
    event: MessageCreated, context: BaseContext, services: Services
) -> None:
    comment = user_message_text(event)
    photos = await remember_photos(event, context)
    if not comment and not photos:
        return

    data = await context.get_data()
    updated = data.get(DRAFT, "")
    if comment:
        updated = await services.ai.refine(updated, comment)
        await context.update_data(**{DRAFT: updated})

    triage = services.triage.preview(data[CATEGORY], data[IS_EMERGENCY])
    await render(
        event, context, texts.draft(updated, triage, photos), keyboards.draft()
    )


@router.message_callback(callbacks.is_action(callbacks.DRAFT_RESTART))
async def on_restart(event: MessageCallback, context: BaseContext) -> None:
    await reset_scenario(context)
    await render(
        event,
        context,
        texts.choose_category(),
        keyboards.categories_menu(),
        notification="Начинаем заново",
    )


@router.message_callback(callbacks.is_action(callbacks.DRAFT_DONE))
async def on_submit(
    event: MessageCallback, context: BaseContext, services: Services
) -> None:
    data = await context.get_data()
    if not data.get(DRAFT):
        await render(
            event,
            context,
            texts.choose_category(),
            keyboards.categories_menu(),
            notification="Черновик не найден, начнём заново",
        )
        return

    await render(event, context, texts.submitting(), keyboards.draft())
    try:
        ticket = await register_once(event, context, services, data)
    except ResidentNotBoundError:
        await show_building_choice(event, context, services, pending_problem=True)
        return
    except Exception:  # noqa: BLE001 - any storage failure: keep the draft, offer retry
        logger.exception("Ticket registration failed")
        await render(event, context, texts.submit_failed(), keyboards.retry_submit())
        return

    await reset_scenario(context)
    await render(
        event,
        context,
        texts.submitted(ticket),
        keyboards.after_submit(),
        notification=f"Заявка № {ticket.number} зарегистрирована",
    )


async def analyze_and_render(
    event: MessageCreated | MessageCallback, context: BaseContext, services: Services
) -> None:
    """Ask the next clarifying question, or triage and show the draft."""

    data = await context.get_data()
    turns = [DialogTurn(**turn) for turn in data.get(TURNS, [])]
    analysis: Analysis = await services.ai.analyze(
        turns, category_code=data.get(CATEGORY)
    )

    if not analysis.is_ready or not analysis.draft:
        question = analysis.question or "Расскажите, пожалуйста, подробнее."
        await append_turn(context, "bot", question)
        await render(
            event,
            context,
            texts.clarifying(question, analysis.explanation),
            keyboards.collecting(),
        )
        return

    complaint = " ".join(turn.text for turn in turns if turn.role == "user")
    triage = await services.triage.execute(complaint, category_hint=data.get(CATEGORY))
    await context.update_data(
        **{
            DRAFT: analysis.draft,
            CATEGORY: triage.category_code,
            IS_EMERGENCY: triage.is_emergency,
        }
    )
    await show_draft_or_confirmation(event, context, analysis.draft, triage)


async def show_draft_or_confirmation(
    event: MessageCreated | MessageCallback,
    context: BaseContext,
    draft: str,
    triage: TriageResult,
) -> None:
    if triage.needs_emergency_confirmation:
        await context.set_state(CreateRequest.confirming_emergency)
        await render(
            event, context, texts.emergency_question(), keyboards.emergency_question()
        )
        return

    await context.set_state(CreateRequest.editing_draft)
    data = await context.get_data()
    photos = len(data.get(PHOTOS) or [])
    await render(event, context, texts.draft(draft, triage, photos), keyboards.draft())


async def register_once(
    event: MessageCallback, context: BaseContext, services: Services, data: dict
) -> TicketView:
    """Create the ticket; a retry after a failure never creates a duplicate."""

    chat_id, _ = event.get_ids()
    user_id = sender_id(event)
    if data.get(TICKET_ID):
        return await services.get_ticket.execute(UUID(data[TICKET_ID]), user_id)

    ticket = await services.create_ticket.execute(
        CreateTicketCommand(
            reporter_id=user_id,
            chat_id=chat_id,
            category_code=data[CATEGORY],
            is_emergency=bool(data[IS_EMERGENCY]),
            description=data[DRAFT],
            photos=tuple(media.from_dicts(data.get(PHOTOS))),
        )
    )
    await context.update_data(**{TICKET_ID: str(ticket.id)})
    return ticket


async def remember_photos(event: MessageCreated, context: BaseContext) -> int:
    """Keep photos of the message for the ticket; returns how many are kept."""

    data = await context.get_data()
    kept = media.from_dicts(data.get(PHOTOS))
    new = media.message_photos(event)
    known = {photo.token for photo in kept}
    kept += [photo for photo in new if photo.token not in known]
    kept = kept[:MAX_PHOTOS]
    if new:
        await context.update_data(**{PHOTOS: media.to_dicts(kept)})
    return len(kept)


async def append_turn(context: BaseContext, role: str, text: str) -> None:
    data = await context.get_data()
    turns = [*data.get(TURNS, []), {"role": role, "text": text}]
    await context.update_data(**{TURNS: turns})


async def reset_scenario(context: BaseContext) -> None:
    """Clear scenario data but keep the link to the current screen message."""

    await context.set_state(None)
    await context.update_data(**dict.fromkeys(SCENARIO_KEYS))
