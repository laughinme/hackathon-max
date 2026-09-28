"""The "problem -> draft with a legal deadline" dialog, as in the bot.

The mini-app holds the conversation and sends it whole on every step, so a
closed app loses nothing on the server and there is no state to clean up.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.http.deps import IdentityDep, ServicesDep
from api.http.v1.schemas.intake import (
    AnalyzeIn,
    DraftStepOut,
    PreviewIn,
    RefineIn,
    RefineOut,
    TriageOut,
)
from application.housing.identity import Identity
from application.ports.ai import DialogTurn
from domain.housing.exceptions import ResidentNotBoundError
from domain.tickets.catalog import get_category

router = APIRouter(prefix="/intake", tags=["intake"])


def _require_residency(identity: Identity) -> None:
    if identity.residency is None:
        raise ResidentNotBoundError()


@router.post(
    "/analyze",
    response_model=DraftStepOut,
    summary="Next clarifying question, or the draft with category and deadline",
)
async def analyze(
    body: AnalyzeIn, identity: IdentityDep, services: ServicesDep
) -> DraftStepOut:
    _require_residency(identity)
    category = get_category(body.category_code).code if body.category_code else None
    turns = [DialogTurn(role=turn.role, text=turn.text) for turn in body.turns]
    step = await services.draft_complaint.execute(turns, category)
    return DraftStepOut.from_step(step)


@router.post(
    "/preview",
    response_model=TriageOut,
    summary="Deadline after the resident answered whether it is an emergency",
)
async def preview(
    body: PreviewIn, identity: IdentityDep, services: ServicesDep
) -> TriageOut:
    _require_residency(identity)
    result = services.triage.preview(
        get_category(body.category_code).code, body.is_emergency
    )
    return TriageOut.from_result(result)


@router.post(
    "/refine",
    response_model=RefineOut,
    summary="Edit the draft by the resident's remark",
)
async def refine(
    body: RefineIn, identity: IdentityDep, services: ServicesDep
) -> RefineOut:
    _require_residency(identity)
    return RefineOut(draft=await services.ai.refine(body.draft, body.comment))
