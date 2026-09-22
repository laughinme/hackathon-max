"""Тесты HTTP-контракта: сервис отвечает даже без обученных моделей."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mlsvc.main import app


def test_health_is_always_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_models_not_loaded() -> None:
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["category_model_loaded"] is False
    assert body["emergency_model_loaded"] is False


def test_classify_returns_503_without_models() -> None:
    with TestClient(app) as client:
        response = client.post("/classify", json={"text": "течёт кран"})

    assert response.status_code == 503
