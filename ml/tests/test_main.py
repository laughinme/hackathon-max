"""Тесты HTTP-контракта: сервис отвечает даже без обученных моделей.

Модели подменяются на пути во временной папке — иначе результат зависел бы
от того, лежат ли уже обученные `.cbm` в `models/` у того, кто запускает.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mlsvc import main
from mlsvc.classifier import ClassifierModels


@pytest.fixture
def client_without_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setattr(
        main,
        "models",
        ClassifierModels(
            category_model_path=tmp_path / "category.cbm",
            emergency_model_path=tmp_path / "emergency.cbm",
        ),
    )
    with TestClient(main.app) as client:
        yield client


def test_health_is_always_ok(client_without_models: TestClient) -> None:
    response = client_without_models.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_models_not_loaded(client_without_models: TestClient) -> None:
    response = client_without_models.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["category_model_loaded"] is False
    assert body["emergency_model_loaded"] is False


def test_classify_returns_503_without_models(
    client_without_models: TestClient,
) -> None:
    response = client_without_models.post("/classify", json={"text": "течёт кран"})

    assert response.status_code == 503
