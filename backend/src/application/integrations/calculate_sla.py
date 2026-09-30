"""The legal deadline as a service: a CRM keeps its tickets and asks us for
the deadline and its legal basis (INTEGRATION_IDEAS K-01)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.ports.clock import Clock
from domain.tickets.catalog import OTHER, get_category
from domain.tickets.enums import ResponsibleParty
from domain.tickets.responsibility import responsibility_for
from domain.tickets.sla import DEFAULT_TIMEZONE, SlaPolicy


@dataclass(frozen=True, slots=True)
class SlaQuote:
    category_code: str
    category_title: str
    is_emergency: bool
    registered_at: datetime
    react_by: datetime | None
    resolve_by: datetime
    legal_basis: str
    responsible_party: ResponsibleParty
    responsibility_basis: str
    #: The rule comes from secondary sources and waits for a legal check.
    needs_verification: bool
    warnings: tuple[str, ...]


class CalculateSla:
    def __init__(self, sla: SlaPolicy, clock: Clock) -> None:
        self._sla = sla
        self._clock = clock

    def execute(
        self,
        category_code: str,
        is_emergency: bool,
        registered_at: datetime | None = None,
    ) -> SlaQuote:
        warnings: list[str] = []
        category = get_category(category_code)
        if category is OTHER and category_code != OTHER.code:
            warnings.append(
                f"Unknown category {category_code!r}: the general rule is used; "
                "see GET /reference for the codes"
            )
        at = registered_at or self._clock.now()
        if at.tzinfo is None:
            warnings.append("registered_at has no time zone: read as Moscow time")
            at = at.replace(tzinfo=DEFAULT_TIMEZONE)
        deadlines = self._sla.deadlines(category.code, is_emergency, at)
        responsibility = responsibility_for(category.code)
        return SlaQuote(
            category_code=category.code,
            category_title=category.title,
            is_emergency=is_emergency,
            registered_at=at,
            react_by=deadlines.react_by,
            resolve_by=deadlines.resolve_by,
            legal_basis=deadlines.legal_basis,
            responsible_party=responsibility.party,
            responsibility_basis=responsibility.legal_basis,
            needs_verification=self._sla.rule_for(
                category.code, is_emergency
            ).needs_verification,
            warnings=tuple(warnings),
        )
