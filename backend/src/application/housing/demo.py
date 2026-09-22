"""Demo-only helpers so checkers can walk both sides with one MAX account."""

from __future__ import annotations

from application.housing.identity import Identity, load_identity
from application.ports.clock import Clock
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.housing.entities import Building, Dispatcher
from domain.housing.exceptions import BuildingNotFoundError


class BecomeDemoDispatcher:
    """Make the user a dispatcher of the demo management company."""

    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    async def execute(self, max_user_id: int) -> Identity:
        async with self._uow_factory() as uow:
            company = await uow.housing.get_demo_company()
            if company is None:
                raise BuildingNotFoundError()
            await uow.housing.save_dispatcher(
                Dispatcher(
                    max_user_id=max_user_id,
                    company_id=company.id,
                    joined_at=self._clock.now(),
                )
            )
            await uow.commit()
            return await load_identity(uow, max_user_id)


class ListDemoBuildings:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, limit: int = 3) -> list[Building]:
        async with self._uow_factory() as uow:
            return await uow.housing.list_demo_buildings(limit)
