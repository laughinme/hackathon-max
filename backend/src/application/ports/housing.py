"""Persistence port for buildings, companies, residents and dispatchers."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from domain.housing.entities import (
    Building,
    Dispatcher,
    ManagementCompany,
    Resident,
)


class HousingRepository(Protocol):
    async def get_building(self, building_id: UUID) -> Building | None: ...

    async def get_building_by_code(self, code: str) -> Building | None: ...

    async def list_demo_buildings(self, limit: int) -> list[Building]: ...

    async def get_company(self, company_id: UUID) -> ManagementCompany | None: ...

    async def get_demo_company(self) -> ManagementCompany | None: ...

    async def get_resident(self, max_user_id: int) -> Resident | None: ...

    async def save_resident(self, resident: Resident) -> None: ...

    async def get_dispatcher(self, max_user_id: int) -> Dispatcher | None: ...

    async def save_dispatcher(self, dispatcher: Dispatcher) -> None: ...
