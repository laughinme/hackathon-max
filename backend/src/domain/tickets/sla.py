"""Legal deadlines for a ticket: who must react and by when, and why.

Every rule carries its legal basis, so the bot can show the resident where a
deadline comes from. Values marked `needs_verification=True` are taken from
secondary sources and must be checked against the primary text before the
demo (docs/DATA.md §2, owner: product role).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from domain.tickets.calendar import add_working_days

DEFAULT_TIMEZONE = ZoneInfo("Europe/Moscow")


@dataclass(frozen=True, slots=True)
class SlaRule:
    """How fast a problem of a given kind must be handled."""

    resolve_within: timedelta | None = None
    resolve_working_days: int | None = None
    react_within: timedelta | None = None
    legal_basis: str = ""
    needs_verification: bool = True


@dataclass(frozen=True, slots=True)
class Deadlines:
    """Concrete deadlines computed for a ticket."""

    resolve_by: datetime
    react_by: datetime | None
    legal_basis: str


EMERGENCY_RULE = SlaRule(
    react_within=timedelta(minutes=30),
    resolve_within=timedelta(days=3),
    legal_basis=(
        "ПП РФ № 416, п. 13: аварийно-диспетчерская служба локализует аварию "
        "не позднее 30 минут и устраняет её не позднее 3 суток"
    ),
)

ROUTINE_RULES: dict[str, SlaRule] = {
    "lift": SlaRule(
        resolve_within=timedelta(days=1),
        legal_basis="Правила № 170, прил. 2: неисправность лифта — до 1 суток",
    ),
    "water": SlaRule(
        resolve_within=timedelta(days=1),
        legal_basis=(
            "Правила № 170, прил. 2: течи в кранах и трубопроводах — до 1 суток"
        ),
    ),
    "heating": SlaRule(
        resolve_within=timedelta(days=1),
        legal_basis=(
            "Правила № 170, прил. 2: неисправности системы отопления — до 1 суток"
        ),
    ),
    "light": SlaRule(
        resolve_within=timedelta(days=7),
        legal_basis=(
            "Правила № 170, прил. 2: неисправности освещения мест общего "
            "пользования — до 7 суток"
        ),
    ),
    "door": SlaRule(
        resolve_within=timedelta(days=1),
        legal_basis=(
            "Правила № 170, прил. 2: неисправности входных дверей и "
            "заполнений — до 1 суток"
        ),
    ),
    "cleaning": SlaRule(
        resolve_within=timedelta(days=1),
        legal_basis=(
            "ПП РФ № 290 (минимальный перечень работ); срок 1 сутки — "
            "допущение, уточняется договором управления"
        ),
    ),
}

FALLBACK_RULE = SlaRule(
    resolve_working_days=10,
    legal_basis="ПП РФ № 416, пп. 34–36: ответ на иное обращение — 10 рабочих дней",
)


class SlaPolicy:
    """Pure function object: (category, emergency, created_at) -> Deadlines."""

    def __init__(self, timezone: ZoneInfo = DEFAULT_TIMEZONE) -> None:
        self._timezone = timezone

    def rule_for(self, category_code: str, is_emergency: bool) -> SlaRule:
        if is_emergency:
            return EMERGENCY_RULE
        return ROUTINE_RULES.get(category_code, FALLBACK_RULE)

    def deadlines(
        self, category_code: str, is_emergency: bool, created_at: datetime
    ) -> Deadlines:
        rule = self.rule_for(category_code, is_emergency)
        local_start = created_at.astimezone(self._timezone)

        if rule.resolve_working_days is not None:
            resolve_by = add_working_days(local_start, rule.resolve_working_days)
        elif rule.resolve_within is not None:
            resolve_by = local_start + rule.resolve_within
        else:  # pragma: no cover - guarded by the rule tables above
            raise ValueError("SLA rule has no resolution deadline")

        react_by = local_start + rule.react_within if rule.react_within else None
        return Deadlines(
            resolve_by=resolve_by, react_by=react_by, legal_basis=rule.legal_basis
        )
