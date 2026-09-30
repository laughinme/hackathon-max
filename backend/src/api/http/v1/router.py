from __future__ import annotations

from fastapi import APIRouter

from api.http.v1 import housing, intake, integrations, me, reference, tickets

router = APIRouter(prefix="/api/v1")
router.include_router(me.router)
router.include_router(housing.router)
router.include_router(tickets.router)
router.include_router(intake.router)
router.include_router(reference.router)
router.include_router(integrations.router)
