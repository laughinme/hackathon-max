"""Who a MAX user is in our system: resident of a building, dispatcher, both."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from application.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class ResidencyView:
    building_id: UUID
    building_code: str
    address: str
    company_id: UUID
    company_name: str
    company_phone: str


@dataclass(frozen=True, slots=True)
class DispatcherView:
    company_id: UUID
    company_name: str


@dataclass(frozen=True, slots=True)
class Identity:
    max_user_id: int
    residency: ResidencyView | None
    dispatcher: DispatcherView | None


class IdentifyUser:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, max_user_id: int) -> Identity:
        async with self._uow_factory() as uow:
            return await load_identity(uow, max_user_id)


async def load_identity(uow: UnitOfWork, max_user_id: int) -> Identity:
    residency = None
    resident = await uow.housing.get_resident(max_user_id)
    if resident is not None:
        building = await uow.housing.get_building(resident.building_id)
        company = building and await uow.housing.get_company(building.company_id)
        if building is not None and company is not None:
            residency = ResidencyView(
                building_id=building.id,
                building_code=building.code,
                address=building.address,
                company_id=company.id,
                company_name=company.name,
                company_phone=company.phone,
            )

    dispatcher_view = None
    dispatcher = await uow.housing.get_dispatcher(max_user_id)
    if dispatcher is not None:
        company = await uow.housing.get_company(dispatcher.company_id)
        if company is not None:
            dispatcher_view = DispatcherView(
                company_id=company.id, company_name=company.name
            )

    return Identity(max_user_id, residency, dispatcher_view)
