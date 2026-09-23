"""REST and webhook wiring (no network: lifespan is not started)."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.http.app import mount_api
from app.main import WEBHOOK_PATH, create_app
from application.tickets.create_ticket import CreateTicketCommand
from infrastructure.max.init_data import sign_init_data
from tests.fakes import BOT_TOKEN, CONFIG, World, make_world

RESIDENT, DISPATCHER = 42, 7


def tma(world: World, user_id: int, age: timedelta = timedelta(0)) -> dict[str, str]:
    auth_date = int((world.clock.now() - age).timestamp())
    fields = {
        "auth_date": str(auth_date),
        "query_id": "q-1",
        "user": json.dumps({"id": user_id, "first_name": "Тест"}),
    }
    return {"Authorization": f"tma {sign_init_data(fields, BOT_TOKEN)}"}


@pytest.fixture
async def world() -> World:
    world = make_world()
    await world.services.bind_resident.execute(RESIDENT, "psk001")
    world.add_dispatcher(DISPATCHER)
    await world.services.create_ticket.execute(
        CreateTicketCommand(RESIDENT, RESIDENT, "lift", False, "Лифт не работает")
    )
    return world


def client_for(world: World) -> TestClient:
    app = FastAPI()
    mount_api(app, world.services)
    return TestClient(app)


def test_me_with_signed_init_data(world):
    response = client_for(world).get("/api/v1/me", headers=tma(world, RESIDENT))
    assert response.status_code == 200
    body = response.json()
    assert body["residency"]["building_code"] == "psk001"
    assert body["dispatcher"] is None and body["demo_mode"] is True


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "tma auth_date=1&user=%7B%7D&hash=deadbeef"},
        {"Authorization": "dev 42"},  # dev auth is off by default
    ],
)
def test_rejects_unsigned_or_forged_requests(world, headers):
    response = client_for(world).get("/api/v1/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["error_code"] == "invalid_init_data"


def test_rejects_expired_init_data(world):
    headers = tma(world, RESIDENT, age=timedelta(hours=2))
    assert client_for(world).get("/api/v1/me", headers=headers).status_code == 401


async def test_dev_auth_only_when_enabled():
    world = make_world(dev_auth_enabled=True)
    response = client_for(world).get("/api/v1/me", headers={"Authorization": "dev 42"})
    assert response.status_code == 200


def test_dispatcher_moves_ticket_and_resident_confirms(world):
    client = client_for(world)
    [ticket] = client.get("/api/v1/tickets", headers=tma(world, RESIDENT)).json()
    assert ticket["available_statuses"] == []

    queue = client.get("/api/v1/dispatcher/queue", headers=tma(world, DISPATCHER))
    assert [t["id"] for t in queue.json()] == [ticket["id"]]
    assert "done" in queue.json()[0]["available_statuses"]

    done = client.post(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "done", "comment": "заменили плату"},
        headers=tma(world, DISPATCHER),
    )
    assert done.status_code == 200 and done.json()["status"] == "done"

    confirmed = client.post(
        f"/api/v1/tickets/{ticket['id']}/confirmation",
        json={"resolved": True},
        headers=tma(world, RESIDENT),
    )
    assert confirmed.json()["status"] == "confirmed"


def test_resident_cannot_use_dispatcher_endpoints(world):
    client = client_for(world)
    [ticket] = client.get("/api/v1/tickets", headers=tma(world, RESIDENT)).json()
    assert (
        client.get("/api/v1/dispatcher/queue", headers=tma(world, RESIDENT)).status_code
        == 403
    )
    response = client.post(
        f"/api/v1/tickets/{ticket['id']}/status",
        json={"status": "done"},
        headers=tma(world, RESIDENT),
    )
    assert response.status_code == 403


def test_illegal_transition_is_conflict(world):
    client = client_for(world)
    [ticket] = client.get("/api/v1/tickets", headers=tma(world, RESIDENT)).json()
    response = client.post(
        f"/api/v1/tickets/{ticket['id']}/confirmation",
        json={"resolved": True},
        headers=tma(world, RESIDENT),
    )
    assert response.status_code == 409


def test_webhook_rejects_missing_or_wrong_secret():
    config = replace(
        CONFIG,
        bot_mode="webhook",
        webhook_url="https://bot.example.ru/webhooks/max",
        webhook_secret="s3cret-value",
    )
    client = TestClient(create_app(config))
    assert client.post(WEBHOOK_PATH, json={}).status_code == 403
    wrong = {"X-Max-Bot-Api-Secret": "wrong"}
    assert client.post(WEBHOOK_PATH, json={}, headers=wrong).status_code == 403


async def test_webhook_answers_200_even_if_processing_fails():
    """Processing runs in the background; its failure must not become a 5xx."""

    import asyncio

    from api.webhooks.max import WebhookReceiver

    class ExplodingDispatcher:
        async def handle(self, event):
            raise RuntimeError("handler bug")

    receiver = WebhookReceiver(ExplodingDispatcher(), bot=None, secret="s3cret-value")  # type: ignore[arg-type]
    app = FastAPI()
    receiver.mount(app, WEBHOOK_PATH)
    client = TestClient(app)
    ok = client.post(
        WEBHOOK_PATH,
        json={"update_type": "unknown_type"},
        headers={"X-Max-Bot-Api-Secret": "s3cret-value"},
    )
    assert ok.status_code == 200 and ok.json() == {"ok": True}
    await asyncio.sleep(0)


def test_polling_mode_has_no_webhook_route():
    client = TestClient(create_app(CONFIG))
    assert client.post(WEBHOOK_PATH, json={}).status_code == 404
    assert client.get("/health").json() == {"status": "ok", "bot_mode": "polling"}


def test_escalation_after_the_deadline_only(world):
    client = client_for(world)
    [ticket] = client.get("/api/v1/tickets", headers=tma(world, RESIDENT)).json()
    assert ticket["can_escalate"] is False and ticket["escalated_at"] is None
    url = f"/api/v1/tickets/{ticket['id']}/escalation"

    early = client.post(url, headers=tma(world, RESIDENT))
    assert early.status_code == 409
    assert early.json()["error_code"] == "ticket_not_overdue"

    world.clock.advance(timedelta(days=2))
    late = client.post(url, headers=tma(world, RESIDENT))
    assert late.status_code == 202
    assert late.json()["escalated_at"] is not None

    queue = client.get("/api/v1/dispatcher/queue", headers=tma(world, DISPATCHER))
    assert queue.json()[0]["can_escalate"] is False  # only the reporter sees it
