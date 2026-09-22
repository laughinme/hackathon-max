"""Bind a MAX user to a building by its short code (QR in the entrance, deep link)."""

from __future__ import annotations

from application.housing.identity import Identity, load_identity
from application.ports.clock import Clock
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.housing.entities import ResidencyKind, Resident
from domain.housing.exceptions import BuildingNotFoundError


class BindResident:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, max_user_id: int, building_code: str) -> Identity:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            building = await uow.housing.get_building_by_code(building_code.strip())
            if building is None:
                raise BuildingNotFoundError()

            resident = await uow.housing.get_resident(max_user_id)
            if resident is None:
                resident = Resident(
                    max_user_id=max_user_id,
                    building_id=building.id,
                    kind=ResidencyKind.UNKNOWN,
                    joined_at=now,
                )
            elif resident.building_id != building.id:
                resident.move_to(building.id, now)
            await uow.housing.save_resident(resident)
            await uow.commit()
            return await load_identity(uow, max_user_id)
