"""DATA-API.yaml stays true: its checks run against the app with test accounts."""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.http.app import mount_api
from api.webhooks.max import WebhookReceiver
from app.main import WEBHOOK_PATH
from infrastructure.seed.test_accounts import ensure_test_accounts
from scripts.check_api import run_checks
from tests.fakes import BOT_TOKEN, make_world


async def test_every_documented_check_passes():
    world = make_world()
    await ensure_test_accounts(world.uow, world.clock)
    app = FastAPI(openapi_url="/api/openapi.json")
    mount_api(app, world.services)
    WebhookReceiver(None, None, "secret").mount(app, WEBHOOK_PATH)  # type: ignore[arg-type]

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "bot_mode": "webhook"}

    @app.get("/ready")
    async def ready() -> dict[str, str]:
        return {"database": "ok"}

    client = TestClient(app)

    def call(
        method: str, path: str, headers: dict[str, str], body: Any
    ) -> tuple[int, dict[str, Any]]:
        response = client.request(method, path, headers=headers, json=body)
        try:
            parsed = response.json()
        except ValueError:
            parsed = {}
        return response.status_code, parsed if isinstance(parsed, dict) else {}

    results = run_checks(call, BOT_TOKEN)
    failed = [(check["id"], status) for check, status, ok in results if not ok]
    assert failed == []
    assert len(results) == 22
