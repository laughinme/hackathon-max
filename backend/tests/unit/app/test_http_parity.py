"""Mini-app endpoints that repeat the bot: building choice, intake, house tools."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.fakes import World, make_world
from tests.unit.app.test_http import client_for, tma

NEWCOMER, RESIDENT = 55, 42


@pytest.fixture
async def world() -> World:
    world = make_world()
    await world.services.bind_resident.execute(RESIDENT, "psk001")
    return world


@pytest.fixture
def client(world) -> TestClient:
    return client_for(world)


def test_newcomer_picks_a_demo_building(world, client):
    headers = tma(world, NEWCOMER)
    buildings = client.get("/api/v1/buildings/demo", headers=headers).json()
    assert [b["code"] for b in buildings] == ["psk001", "psk002"]

    me = client.put(
        "/api/v1/me/residency", json={"building_code": "psk002"}, headers=headers
    )
    assert me.status_code == 200
    assert me.json()["residency"]["address"] == "ул. Тестовая, 2"

    unknown = client.put(
        "/api/v1/me/residency", json={"building_code": "nope"}, headers=headers
    )
    assert unknown.status_code == 404
    assert unknown.json()["error_code"] == "building_not_found"


def test_intake_dialog_then_ticket(world, client):
    headers = tma(world, RESIDENT)
    turns = [{"role": "user", "text": "Проблема: Лифт"}]
    first = client.post(
        "/api/v1/intake/analyze",
        json={"turns": turns, "category_code": "lift"},
        headers=headers,
    ).json()
    assert first["ready"] is False and first["question"]

    turns += [
        {"role": "bot", "text": first["question"]},
        {"role": "user", "text": "Второй подъезд, стоит на 5 этаже"},
    ]
    step = client.post(
        "/api/v1/intake/analyze",
        json={"turns": turns, "category_code": "lift"},
        headers=headers,
    ).json()
    assert step["ready"] is True
    assert step["triage"]["category_code"] == "lift"
    assert step["triage"]["resolve_by"]

    refined = client.post(
        "/api/v1/intake/refine",
        json={"draft": step["draft"], "comment": "Кнопки не горят"},
        headers=headers,
    ).json()
    assert "Кнопки не горят" in refined["draft"]

    created = client.post(
        "/api/v1/tickets",
        json={
            "category_code": "lift",
            "is_emergency": False,
            "description": refined["draft"],
        },
        headers=headers,
    )
    assert created.status_code == 201
    ticket = created.json()
    assert ticket["status"] == "registered"
    assert ticket["building_address"] == "ул. Тестовая, 1"
    mine = client.get("/api/v1/tickets", headers=headers).json()
    assert [t["id"] for t in mine] == [ticket["id"]]


def test_emergency_answer_changes_the_deadline(world, client):
    headers = tma(world, RESIDENT)
    urgent, calm = (
        client.post(
            "/api/v1/intake/preview",
            json={"category_code": "water", "is_emergency": answer},
            headers=headers,
        ).json()
        for answer in (True, False)
    )
    assert urgent["is_emergency"] and urgent["react_by"]
    assert not calm["is_emergency"] and calm["react_by"] is None


def test_intake_needs_a_building(world, client):
    headers = tma(world, NEWCOMER)
    body = {"turns": [{"role": "user", "text": "Течёт"}]}
    response = client.post("/api/v1/intake/analyze", json=body, headers=headers)
    assert response.status_code == 409
    assert response.json()["error_code"] == "resident_not_bound"
    ticket = {"category_code": "water", "is_emergency": True, "description": "Течёт"}
    assert (
        client.post("/api/v1/tickets", json=ticket, headers=headers).status_code == 409
    )


def test_house_pulse_and_signed_leaflet(world, client):
    house = client.get("/api/v1/me/building", headers=tma(world, RESIDENT)).json()
    assert house["address"] == "ул. Тестовая, 1"
    assert house["pulse"]["total"] == 0
    assert house["leaflet_filename"] == "domovoy-psk001.pdf"

    pdf = client.get(house["leaflet_path"])  # no Authorization: downloadFile
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    forged = house["leaflet_path"].replace("sig=", "sig=0")
    assert client.get(forged).status_code == 404


def test_demo_dispatcher_and_forget_me(world, client):
    headers = tma(world, RESIDENT)
    me = client.post("/api/v1/me/demo-dispatcher", headers=headers).json()
    assert me["dispatcher"]["company_name"] == "УО Тест"

    forgotten = client.delete("/api/v1/me", headers=headers)
    assert forgotten.status_code == 200
    me = client.get("/api/v1/me", headers=headers).json()
    assert me["residency"] is None and me["dispatcher"] is None


async def test_demo_dispatcher_is_off_outside_demo():
    world = make_world(demo_mode=False)
    response = client_for(world).post(
        "/api/v1/me/demo-dispatcher", headers=tma(world, RESIDENT)
    )
    assert response.status_code == 403


def test_reference_lists(world, client):
    categories = client.get("/api/v1/reference/categories").json()
    assert categories[-1]["code"] == "other"
    assert all(c["clarifying_question"] for c in categories)
    guide = client.get("/api/v1/reference/responsibility").json()
    assert any(entry["who"].startswith("Государственная") for entry in guide)
