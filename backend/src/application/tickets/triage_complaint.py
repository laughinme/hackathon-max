"""Triage a complaint before registration: category, emergency, deadline preview.

The classifier (CatBoost service or rules, DECISIONS D-005/D-006) decides the
category and whether it is an emergency. Both feed the legal deadline. When
the classifier is unsure about emergency, the ticket is treated as an
emergency by default (fail-safe from D-005) and the adapter must ask the
resident to confirm.
"""

from __future__ import annotations

from dataclasses import dataclass

from application.ports.classifier import Classifier
from application.ports.clock import Clock
from domain.tickets.responsibility import Responsibility, responsibility_for
from domain.tickets.sla import Deadlines, SlaPolicy

OTHER_CATEGORY = "other"


@dataclass(frozen=True, slots=True)
class TriageResult:
    category_code: str
    is_emergency: bool
    needs_emergency_confirmation: bool
    responsibility: Responsibility
    deadlines_preview: Deadlines


class TriageComplaint:
    def __init__(
        self,
        classifier: Classifier,
        sla_policy: SlaPolicy,
        clock: Clock,
        confidence_threshold: float,
    ) -> None:
        self._classifier = classifier
        self._sla = sla_policy
        self._clock = clock
        self._threshold = confidence_threshold

    async def execute(self, text: str, category_hint: str | None) -> TriageResult:
        classification = await self._classifier.classify(text)

        category = classification.category_code
        if category_hint and category_hint != OTHER_CATEGORY:
            category = category_hint  # the resident picked it explicitly

        unsure = classification.emergency_confidence < self._threshold
        is_emergency = classification.is_emergency or unsure
        return self._result(category, is_emergency, needs_confirmation=unsure)

    def preview(self, category_code: str, is_emergency: bool) -> TriageResult:
        """Recompute after the resident confirmed or denied an emergency."""

        return self._result(category_code, is_emergency, needs_confirmation=False)

    def _result(
        self, category: str, is_emergency: bool, *, needs_confirmation: bool
    ) -> TriageResult:
        return TriageResult(
            category_code=category,
            is_emergency=is_emergency,
            needs_emergency_confirmation=needs_confirmation,
            responsibility=responsibility_for(category),
            deadlines_preview=self._sla.deadlines(
                category, is_emergency, self._clock.now()
            ),
        )
