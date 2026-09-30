"""The public integration API over HTTP: key auth, the CRM loop, the contract."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.http.app import mount_api
from application.tickets.create_ticket import CreateTicketCommand
from tests.fakes import World, make_world
from tests.unit.app.test_http import tma

RESIDENT, DISPATCHER = 42, 7
BASE = "/integration/v1"


@pytest.fixture
async def world() -> World:
    world = make_world()
    await world.services.bind_resident.execute(RESIDENT, "psk001")
    world.add_dispatcher(DISPATCHER)
    await world.services.create_ticket.execute(
        CreateTicketCommand(RESIDENT, None, "lift", False, "Лифт не работает")
    )
    return world


@pytest.fixture
def client(world: World) -> TestClient:
    app = FastAPI()
    mount_api(app, world.services)
    return TestClient(app)


def connect(client: TestClient, world: World) -> dict[str, str]:
    response = client.post(
        "/api/v1/dispatcher/integrations",
        json={"name": "1С:Жилищный стандарт"},
        headers=tma(world, DISPATCHER),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["docs_url"].endswith("/integration/v1/docs")
    return {"Authorization": f"Bearer {body['api_key']}"}


def test_dispatcher_connects_and_resident_cannot(client, world):
    denied = client.post(
        "/api/v1/dispatcher/integrations", json={}, headers=tma(world, RESIDENT)
    )
    assert denied.status_code == 403

    key = connect(client, world)
    listed = client.get(
        "/api/v1/dispatcher/integrations", headers=tma(world, DISPATCHER)
    )
    [integration] = listed.json()
    assert integration["name"] == "1С:Жилищный стандарт"
    assert (
        key["Authorization"]
        .removeprefix("Bearer ")
        .startswith(integration["key_prefix"])
    )

    revoked = client.delete(
        f"/api/v1/dispatcher/integrations/{integration['id']}",
        headers=tma(world, DISPATCHER),
    )
    assert revoked.status_code == 204
    assert client.get(f"{BASE}/me", headers=key).status_code == 401


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer dmv_nope"}, {"X-Api-Key": "not-a-key"}],
)
def test_integration_api_needs_a_key(client, headers):
    response = client.get(f"{BASE}/tickets", headers=headers)
    assert response.status_code == 401
    assert response.json()["error_code"] == "invalid_api_key"


def test_crm_loop_over_http(client, world):
    key = connect(client, world)
    x_api_key = {"X-Api-Key": key["Authorization"].removeprefix("Bearer ")}
    assert client.get(f"{BASE}/me", headers=x_api_key).status_code == 200

    hook = client.put(
        f"{BASE}/webhook",
        json={"url": "https://crm.example.ru/hook"},
        headers=key,
    ).json()
    assert hook["secret"].startswith("whsec_") and len(hook["event_types"]) == 5
    rejected = client.put(
        f"{BASE}/webhook", json={"url": "http://10.0.0.1/hook"}, headers=key
    )
    assert rejected.status_code == 422

    client.put(
        f"{BASE}/status-map", json={"map": {"WORKING": "in_progress"}}, headers=key
    )
    moved = client.post(
        f"{BASE}/tickets/2026-00001/status",
        json={
            "status": "WORKING",
            "comment": "Мастер выехал",
            "external": {"id": "58391", "number": "АДС-58391"},
        },
        headers=key,
    )
    assert moved.status_code == 200, moved.text
    body = moved.json()
    assert body["applied"] is True
    assert body["ticket"]["status"] == "in_progress"
    assert body["ticket"]["crm_status"] == "WORKING"
    assert body["ticket"]["external"]["number"] == "АДС-58391"

    card = client.get(f"{BASE}/tickets/ext:58391", headers=key).json()
    assert card["number"] == "2026-00001"
    assert card["timeline"][-1]["comment"] == "Мастер выехал"

    confirm = client.post(
        f"{BASE}/tickets/ext:58391/status", json={"status": "confirmed"}, headers=key
    )
    assert confirm.status_code == 409  # only the resident confirms, from done
    unknown = client.post(
        f"{BASE}/tickets/ext:58391/status", json={"status": "PAUSED"}, headers=key
    )
    assert unknown.status_code == 422
    assert unknown.json()["error_code"] == "unknown_status"
    missing = client.get(f"{BASE}/tickets/2099-99999", headers=key)
    assert missing.status_code == 404


def test_feed_tickets_reference_and_sla(client, world):
    key = connect(client, world)
    events = client.get(f"{BASE}/events", params={"after": 0}, headers=key).json()
    assert [e["type"] for e in events["events"]] == ["ticket.created"]
    assert events["next_after"] == events["events"][0]["seq"]

    page = client.get(f"{BASE}/tickets", headers=key).json()
    assert [t["number"] for t in page["tickets"]] == ["2026-00001"]
    assert page["next_cursor"] is None
    bad = client.get(f"{BASE}/tickets", params={"cursor": "%%%"}, headers=key)
    assert bad.status_code == 400

    reference = client.get(f"{BASE}/reference", headers=key).json()
    settable = {s["code"] for s in reference["statuses"] if s["integration_can_set"]}
    assert settable == {"acknowledged", "in_progress", "done", "rejected"}

    sla = client.post(
        f"{BASE}/sla/calculate",
        json={"category_code": "lift", "registered_at": "2026-09-30T09:00:00"},
        headers=key,
    ).json()
    assert sla["resolve_by"].startswith("2026-10-01T09:00:00+03:00")
    assert sla["warnings"]  # a time without a zone is read as Moscow time


def test_ping_reports_what_the_crm_answered(client, world):
    key = connect(client, world)
    assert client.post(f"{BASE}/webhook/test", headers=key).status_code == 422
    client.put(f"{BASE}/webhook", json={"url": "https://crm.example.ru/h"}, headers=key)
    world.webhooks.answer = {"ok": True}
    ping = client.post(f"{BASE}/webhook/test", headers=key).json()
    assert ping == {
        "ok": True,
        "status_code": 200,
        "error": None,
        "answer": {"ok": True},
    }
    assert world.webhooks.sent[-1][1]["type"] == "ping"


def test_openapi_documents_the_contract_and_webhook(client):
    schema = client.get(f"{BASE}/openapi.json").json()
    assert "/tickets/{ticket_ref}/status" in schema["paths"]
    assert "ticket-event" in schema["webhooks"]
    assert client.get(f"{BASE}/docs").status_code == 200
