"""Reference data the bot shows as buttons and texts: categories, who answers."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from domain.tickets.catalog import CATEGORIES, OTHER
from domain.tickets.enums import ResponsibleParty
from domain.tickets.responsibility_guide import GUIDE

router = APIRouter(prefix="/reference", tags=["reference"])


class CategoryOut(BaseModel):
    code: str
    emoji: str
    title: str
    clarifying_question: str


class GuideEntryOut(BaseModel):
    emoji: str
    situation: str
    party: ResponsibleParty | None
    who: str
    basis: str
    where: str


@router.get(
    "/categories",
    response_model=list[CategoryOut],
    summary="Quick categories with the first clarifying question; 'other' is last",
)
async def categories() -> list[CategoryOut]:
    return [
        CategoryOut(
            code=category.code,
            emoji=category.emoji,
            title=category.title,
            clarifying_question=category.clarifying_question,
        )
        for category in (*CATEGORIES, OTHER)
    ]


@router.get(
    "/responsibility",
    response_model=list[GuideEntryOut],
    summary="Who answers for what around a building, and where to turn",
)
async def responsibility() -> list[GuideEntryOut]:
    return [
        GuideEntryOut(
            emoji=entry.emoji,
            situation=entry.situation,
            party=entry.party,
            who=entry.who,
            basis=entry.basis,
            where=entry.where,
        )
        for entry in GUIDE
    ]
