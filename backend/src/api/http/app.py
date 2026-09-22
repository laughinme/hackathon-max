"""Mount the REST API onto a FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI

from api.http.errors import register_error_handlers
from api.http.v1.router import router as api_v1
from app.services import Services


def mount_api(app: FastAPI, services: Services) -> None:
    app.state.services = services
    register_error_handlers(app)
    app.include_router(api_v1)
