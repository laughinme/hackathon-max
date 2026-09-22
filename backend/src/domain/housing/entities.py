"""Buildings, the organisations that manage them and the people involved."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ResidencyKind(StrEnum):
    OWNER = "owner"
    TENANT = "tenant"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ManagementCompany:
    id: UUID
    name: str
    phone: str
    region: str
    is_demo: bool


@dataclass(frozen=True, slots=True)
class Building:
    """An apartment building. `code` is short and goes into QR deep links."""

    id: UUID
    code: str
    address: str
    company_id: UUID
    is_demo: bool


@dataclass(slots=True)
class Resident:
    """A MAX user bound to one building (MVP: one building per user)."""

    max_user_id: int
    building_id: UUID
    kind: ResidencyKind
    joined_at: datetime
    apartment: str | None = None

    def move_to(self, building_id: UUID, now: datetime) -> None:
        self.building_id = building_id
        self.joined_at = now


@dataclass(frozen=True, slots=True)
class Dispatcher:
    """A management company employee who works the ticket queue."""

    max_user_id: int
    company_id: UUID
    joined_at: datetime
