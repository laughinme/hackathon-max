"""Printable notice for the entrance with a QR code to the bot."""

from __future__ import annotations

from uuid import UUID

from application.ports.documents import Leaflet, LeafletRenderer
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.build_escalation_document import RenderedDocument
from domain.housing.exceptions import BuildingNotFoundError

#: Deep link payload that binds the resident to the building on start.
BUILDING_LINK_PREFIX = "h_"


class BuildLeaflet:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, renderer: LeafletRenderer, bot_link: str
    ) -> None:
        self._uow_factory = uow_factory
        self._renderer = renderer
        self._bot_link = bot_link

    async def execute(self, building_id: UUID) -> RenderedDocument:
        async with self._uow_factory() as uow:
            building = await uow.housing.get_building(building_id)
            company = (
                await uow.housing.get_company(building.company_id) if building else None
            )
        if building is None or company is None:
            raise BuildingNotFoundError()
        leaflet = Leaflet(
            address=building.address,
            link=f"{self._bot_link}?start={BUILDING_LINK_PREFIX}{building.code}",
            company_name=company.name,
            company_phone=company.phone,
            is_demo=building.is_demo,
        )
        return RenderedDocument(
            filename=f"domovoy-{building.code}.pdf",
            content=self._renderer.render(leaflet),
        )
