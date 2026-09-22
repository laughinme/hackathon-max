from __future__ import annotations

from fastapi import APIRouter

from api.http.v1 import me, tickets

router = APIRouter(prefix="/api/v1")
router.include_router(me.router)
router.include_router(tickets.router)
