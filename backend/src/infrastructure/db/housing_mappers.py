"""ORM <-> domain mapping for housing entities."""

from __future__ import annotations

from domain.housing.entities import (
    Building,
    Dispatcher,
    ManagementCompany,
    ResidencyKind,
    Resident,
)
from infrastructure.db.models import (
    BuildingRow,
    DispatcherRow,
    ManagementCompanyRow,
    ResidentRow,
)


def company_to_domain(row: ManagementCompanyRow) -> ManagementCompany:
    return ManagementCompany(
        id=row.id,
        name=row.name,
        phone=row.phone,
        region=row.region,
        is_demo=row.is_demo,
    )


def building_to_domain(row: BuildingRow) -> Building:
    return Building(
        id=row.id,
        code=row.code,
        address=row.address,
        company_id=row.company_id,
        is_demo=row.is_demo,
    )


def resident_to_domain(row: ResidentRow) -> Resident:
    return Resident(
        max_user_id=row.max_user_id,
        building_id=row.building_id,
        kind=ResidencyKind(row.kind),
        joined_at=row.joined_at,
        apartment=row.apartment,
    )


def dispatcher_to_domain(row: DispatcherRow) -> Dispatcher:
    return Dispatcher(
        max_user_id=row.max_user_id, company_id=row.company_id, joined_at=row.joined_at
    )
