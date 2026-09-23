"""Domain errors -> RFC 7807 problem responses (pattern from the team template)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from application.errors import TicketNotFoundError
from domain.errors import DomainError
from domain.housing.exceptions import (
    BuildingNotFoundError,
    NotADispatcherError,
    ResidentNotBoundError,
)
from domain.tickets.exceptions import (
    ActionNotAllowedError,
    IllegalTransitionError,
    NotTicketReporterError,
    TicketNotOverdueError,
)
from infrastructure.max.init_data import InvalidInitDataError

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    InvalidInitDataError: 401,
    NotADispatcherError: 403,
    ActionNotAllowedError: 403,
    NotTicketReporterError: 403,
    TicketNotOverdueError: 409,
    TicketNotFoundError: 404,
    BuildingNotFoundError: 404,
    IllegalTransitionError: 409,
    ResidentNotBoundError: 409,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status = STATUS_BY_ERROR.get(type(exc), 400)
        return JSONResponse(
            status_code=status,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": exc.code,
                "status": status,
                "detail": exc.message,
                "error_code": exc.code,
                "instance": request.url.path,
            },
        )
