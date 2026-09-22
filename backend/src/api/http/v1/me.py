from __future__ import annotations

from fastapi import APIRouter

from api.http.deps import IdentityDep, ServicesDep
from api.http.v1.schemas.me import MeOut

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeOut, summary="Current user: building and roles")
async def get_me(identity: IdentityDep, services: ServicesDep) -> MeOut:
    return MeOut.from_identity(identity, services.config.demo_mode)
