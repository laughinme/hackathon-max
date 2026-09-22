"""FastAPI dependencies: services container and the authenticated MAX user."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from app.services import Services
from application.housing.identity import Identity
from infrastructure.max.init_data import InvalidInitDataError, validate_init_data


def get_services(request: Request) -> Services:
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


async def current_identity(
    services: ServicesDep,
    authorization: Annotated[str | None, Header()] = None,
) -> Identity:
    """`Authorization: tma <WebApp.initData>` from the MAX mini-app.

    With DEV_AUTH_ENABLED=true, `Authorization: dev <max_user_id>` is accepted
    too — for running the frontend outside MAX. Never enable it in production.
    """

    scheme, _, credentials = (authorization or "").partition(" ")
    scheme = scheme.lower()
    config = services.config
    if scheme == "tma" and credentials:
        init_data = validate_init_data(
            credentials, config.bot_token, now=services.clock.now()
        )
        return await services.identify.execute(init_data.user_id)
    if (
        scheme == "dev"
        and config.dev_auth_enabled
        and credentials.lstrip("-").isdigit()
    ):
        return await services.identify.execute(int(credentials))
    raise InvalidInitDataError("missing Authorization: tma <initData>")


IdentityDep = Annotated[Identity, Depends(current_identity)]
