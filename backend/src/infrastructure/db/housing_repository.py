"""SQLAlchemy implementation of the housing repository port."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.housing.entities import (
    Building,
    Dispatcher,
    ManagementCompany,
    Resident,
)
from infrastructure.db.housing_mappers import (
    building_to_domain,
    company_to_domain,
    dispatcher_to_domain,
    resident_to_domain,
)
from infrastructure.db.models import (
    BuildingRow,
    DispatcherRow,
    ManagementCompanyRow,
    ResidentRow,
)


class SqlHousingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_building(self, building_id: UUID) -> Building | None:
        row = await self._session.get(BuildingRow, building_id)
        return building_to_domain(row) if row else None

    async def get_building_by_code(self, code: str) -> Building | None:
        row = await self._session.scalar(
            select(BuildingRow).where(BuildingRow.code == code)
        )
        return building_to_domain(row) if row else None

    async def list_demo_buildings(self, limit: int) -> list[Building]:
        rows = await self._session.scalars(
            select(BuildingRow)
            .where(BuildingRow.is_demo.is_(True))
            .order_by(BuildingRow.code)
            .limit(limit)
        )
        return [building_to_domain(row) for row in rows]

    async def get_company(self, company_id: UUID) -> ManagementCompany | None:
        row = await self._session.get(ManagementCompanyRow, company_id)
        return company_to_domain(row) if row else None

    async def get_demo_company(self) -> ManagementCompany | None:
        row = await self._session.scalar(
            select(ManagementCompanyRow)
            .where(ManagementCompanyRow.is_demo.is_(True))
            .limit(1)
        )
        return company_to_domain(row) if row else None

    async def get_resident(self, max_user_id: int) -> Resident | None:
        row = await self._session.get(ResidentRow, max_user_id)
        return resident_to_domain(row) if row else None

    async def save_resident(self, resident: Resident) -> None:
        await self._session.merge(
            ResidentRow(
                max_user_id=resident.max_user_id,
                building_id=resident.building_id,
                kind=resident.kind.value,
                apartment=resident.apartment,
                joined_at=resident.joined_at,
            )
        )

    async def get_dispatcher(self, max_user_id: int) -> Dispatcher | None:
        row = await self._session.get(DispatcherRow, max_user_id)
        return dispatcher_to_domain(row) if row else None

    async def save_dispatcher(self, dispatcher: Dispatcher) -> None:
        await self._session.merge(
            DispatcherRow(
                max_user_id=dispatcher.max_user_id,
                company_id=dispatcher.company_id,
                joined_at=dispatcher.joined_at,
            )
        )

    async def list_dispatchers(self, company_id: UUID) -> list[Dispatcher]:
        rows = await self._session.scalars(
            select(DispatcherRow)
            .where(DispatcherRow.company_id == company_id)
            .order_by(DispatcherRow.joined_at)
        )
        return [dispatcher_to_domain(row) for row in rows]
