"""Bodies of the intake dialog; the mini-app keeps the turns, not the server."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from application.tickets.draft_complaint import DraftStep
from application.tickets.triage_complaint import TriageResult
from domain.tickets.enums import ResponsibleParty

MAX_TURNS = 20
MAX_TEXT = 2000


class TurnIn(BaseModel):
    role: Literal["user", "bot"]
    text: str = Field(min_length=1, max_length=MAX_TEXT)


class AnalyzeIn(BaseModel):
    turns: list[TurnIn] = Field(min_length=1, max_length=MAX_TURNS)
    category_code: str | None = Field(
        default=None, description="Quick category the resident picked, if any"
    )


class PreviewIn(BaseModel):
    category_code: str
    is_emergency: bool


class RefineIn(BaseModel):
    draft: str = Field(min_length=1, max_length=MAX_TEXT * 2)
    comment: str = Field(min_length=1, max_length=MAX_TEXT)


class RefineOut(BaseModel):
    draft: str


class TriageOut(BaseModel):
    category_code: str
    is_emergency: bool
    needs_emergency_confirmation: bool = Field(
        description="The classifier is unsure: ask the resident whether it is an "
        "emergency, then call /intake/preview with the answer"
    )
    responsible_party: ResponsibleParty
    responsibility_basis: str
    resolve_by: datetime
    react_by: datetime | None
    deadline_basis: str

    @classmethod
    def from_result(cls, result: TriageResult) -> TriageOut:
        deadlines = result.deadlines_preview
        return cls(
            category_code=result.category_code,
            is_emergency=result.is_emergency,
            needs_emergency_confirmation=result.needs_emergency_confirmation,
            responsible_party=result.responsibility.party,
            responsibility_basis=result.responsibility.legal_basis,
            resolve_by=deadlines.resolve_by,
            react_by=deadlines.react_by,
            deadline_basis=deadlines.legal_basis,
        )


class DraftStepOut(BaseModel):
    ready: bool = Field(description="true: `draft` and `triage` are set")
    explanation: str
    question: str | None
    draft: str | None
    triage: TriageOut | None

    @classmethod
    def from_step(cls, step: DraftStep) -> DraftStepOut:
        return cls(
            ready=step.is_ready,
            explanation=step.explanation,
            question=step.question,
            draft=step.draft,
            triage=TriageOut.from_result(step.triage) if step.triage else None,
        )


class TicketCreateIn(BaseModel):
    category_code: str
    is_emergency: bool
    description: str = Field(min_length=1, max_length=MAX_TEXT * 2)
