"""House endpoints: choose a building, demo role, pulse, leaflet, privacy."""

from __future__ import annotations

import hashlib
import hmac
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import Response

from api.http.deps import IdentityDep, ServicesDep
from api.http.v1.schemas.housing import (
    BuildingOut,
    ForgetOut,
    HouseOut,
    PulseOut,
    ResidencyIn,
)
from api.http.v1.schemas.me import MeOut
from application.errors import DemoActionNotAllowedError
from application.housing.build_leaflet import leaflet_filename
from domain.housing.exceptions import BuildingNotFoundError, ResidentNotBoundError

router = APIRouter(tags=["housing"])

LEAFLET_PATH = "/api/v1/buildings/{building_id}/leaflet.pdf"


def leaflet_signature(building_id: UUID, secret: str) -> str:
    message = f"leaflet:{building_id}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()[:32]


@router.get(
    "/buildings/demo",
    response_model=list[BuildingOut],
    summary="Demo buildings to choose from (in real life the QR picks it)",
)
async def demo_buildings(
    _: IdentityDep, services: ServicesDep, limit: int = Query(default=3, ge=1, le=50)
) -> list[BuildingOut]:
    buildings = await services.list_demo_buildings.execute(limit)
    return [BuildingOut.from_building(building) for building in buildings]


@router.put("/me/residency", response_model=MeOut, summary="Bind me to a building")
async def bind_residency(
    body: ResidencyIn, identity: IdentityDep, services: ServicesDep
) -> MeOut:
    updated = await services.bind_resident.execute(
        identity.max_user_id, body.building_code
    )
    return MeOut.from_identity(updated, services.config.demo_mode)


@router.post(
    "/me/demo-dispatcher",
    response_model=MeOut,
    summary="DEMO_MODE only: become a dispatcher of the demo management company",
)
async def become_demo_dispatcher(identity: IdentityDep, services: ServicesDep) -> MeOut:
    if not services.config.demo_mode:
        raise DemoActionNotAllowedError("Demo mode is off")
    updated = await services.become_demo_dispatcher.execute(identity.max_user_id)
    return MeOut.from_identity(updated, services.config.demo_mode)


@router.delete(
    "/me",
    response_model=ForgetOut,
    summary="Forget me: building, roles and the link to my tickets",
)
async def forget_me(identity: IdentityDep, services: ServicesDep) -> ForgetOut:
    detached = await services.forget_user.execute(identity.max_user_id)
    return ForgetOut(detached_tickets=detached)


@router.get(
    "/me/building",
    response_model=HouseOut,
    summary="My building: pulse for 30 days and the QR leaflet",
)
async def my_building(identity: IdentityDep, services: ServicesDep) -> HouseOut:
    residency = identity.residency
    if residency is None:
        raise ResidentNotBoundError()
    pulse = await services.building_pulse.execute(residency.building_id)
    signature = leaflet_signature(residency.building_id, services.config.bot_token)
    path = LEAFLET_PATH.format(building_id=residency.building_id)
    return HouseOut(
        building_code=residency.building_code,
        address=residency.address,
        company_name=residency.company_name,
        company_phone=residency.company_phone,
        pulse=PulseOut.from_pulse(pulse),
        leaflet_path=f"{path}?sig={signature}",
        leaflet_filename=leaflet_filename(residency.building_code),
    )


@router.get(
    LEAFLET_PATH.removeprefix("/api/v1"),
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
    summary="Printable leaflet with a QR code to the bot; the link is signed",
)
async def leaflet(
    building_id: UUID, services: ServicesDep, sig: str = Query(max_length=64)
) -> Response:
    expected = leaflet_signature(building_id, services.config.bot_token)
    if not hmac.compare_digest(sig, expected):
        raise BuildingNotFoundError()  # do not tell a bad link from a missing house
    document = await services.leaflet.execute(building_id)
    return Response(
        content=document.content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{document.filename}"'},
    )
