"""One step of the intake dialog: ask the next question or draft the ticket.

Shared by the bot and the mini-app, so both ask the same questions and show
the same deadline before the resident presses "Send".
"""

from __future__ import annotations

from dataclasses import dataclass

from application.ports.ai import AIService, DialogTurn
from application.tickets.triage_complaint import TriageComplaint, TriageResult

DEFAULT_QUESTION = "Расскажите, пожалуйста, подробнее."


@dataclass(frozen=True, slots=True)
class DraftStep:
    """Either `question` (keep asking) or `draft` with its `triage`."""

    explanation: str
    question: str | None = None
    draft: str | None = None
    triage: TriageResult | None = None

    @property
    def is_ready(self) -> bool:
        return self.draft is not None


class DraftComplaint:
    def __init__(self, ai: AIService, triage: TriageComplaint) -> None:
        self._ai = ai
        self._triage = triage

    async def execute(
        self, turns: list[DialogTurn], category_code: str | None
    ) -> DraftStep:
        analysis = await self._ai.analyze(turns, category_code=category_code)
        if not analysis.is_ready or not analysis.draft:
            return DraftStep(
                explanation=analysis.explanation,
                question=analysis.question or DEFAULT_QUESTION,
            )

        complaint = " ".join(turn.text for turn in turns if turn.role == "user")
        triage = await self._triage.execute(complaint, category_hint=category_code)
        return DraftStep(
            explanation=analysis.explanation, draft=analysis.draft, triage=triage
        )
