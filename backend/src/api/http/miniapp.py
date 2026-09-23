"""Serves the built mini-app (frontend/dist) from the same origin as the API.

One HTTPS domain for the webhook, the REST API and the mini-app: no CORS, one
certificate, one URL to send to the organisers. Hashed assets are cached
forever; index.html is always revalidated so a deploy is picked up at once.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

IMMUTABLE = "public, max-age=31536000, immutable"
REVALIDATE = "no-cache"


class MiniAppFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = (
            IMMUTABLE if path.startswith("assets/") else REVALIDATE
        )
        return response


def mount_miniapp(app: FastAPI, directory: Path) -> None:
    """Mount last: API, webhook and ops routes registered earlier win."""

    app.mount("/", MiniAppFiles(directory=directory, html=True), name="miniapp")
