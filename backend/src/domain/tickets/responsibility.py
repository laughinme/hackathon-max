"""Who is legally responsible for a problem category, and on what basis."""

from __future__ import annotations

from dataclasses import dataclass

from domain.tickets.enums import ResponsibleParty


@dataclass(frozen=True, slots=True)
class Responsibility:
    party: ResponsibleParty
    legal_basis: str


COMMON_PROPERTY = Responsibility(
    party=ResponsibleParty.MANAGEMENT_COMPANY,
    legal_basis="общее имущество МКД: ЖК РФ ст. 161, ПП РФ № 491",
)

# Every current catalog category concerns common property of the building.
# Resource suppliers, capital repair operator and municipality appear once the
# catalog grows (docs/DATA.md §3).
RESPONSIBILITY_BY_CATEGORY: dict[str, Responsibility] = {
    code: COMMON_PROPERTY
    for code in ("water", "light", "heating", "door", "cleaning", "lift", "other")
}


def responsibility_for(category_code: str) -> Responsibility:
    return RESPONSIBILITY_BY_CATEGORY.get(category_code, COMMON_PROPERTY)
