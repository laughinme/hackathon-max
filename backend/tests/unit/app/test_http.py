"""HTTP wiring of the webhook mode (lifespan is not started: no network)."""

from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from app.config import Config
from app.main import WEBHOOK_PATH, create_app

CONFIG = Config(
    bot_token="test-token",
    log_level="INFO",
    database_url="postgresql+asyncpg://user:pass@localhost:1/unused",
    bot_mode="webhook",
    webhook_url="https://bot.example.ru/webhooks/max",
    webhook_secret="s3cret-value",
    http_host="127.0.0.1",
    http_port=8080,
    llm_enabled=False,
    llm_base_url="",
    llm_model="",
    llm_api_key=None,
    llm_timeout_sec=1.0,
    llm_temperature=0.0,
    ml_service_url="http://localhost:1",
    ml_service_timeout_sec=0.1,
    ml_confidence_threshold=0.6,
)


def test_webhook_rejects_requests_without_secret():
    client = TestClient(create_app(CONFIG))
    response = client.post(WEBHOOK_PATH, json={"update_type": "bot_started"})
    assert response.status_code == 403


def test_webhook_rejects_wrong_secret():
    client = TestClient(create_app(CONFIG))
    response = client.post(
        WEBHOOK_PATH,
        json={"update_type": "bot_started"},
        headers={"X-Max-Bot-Api-Secret": "wrong"},
    )
    assert response.status_code == 403


def test_polling_mode_exposes_no_webhook_route():
    client = TestClient(create_app(replace(CONFIG, bot_mode="polling")))
    assert client.post(WEBHOOK_PATH, json={}).status_code == 404
    assert client.get("/health").json() == {"status": "ok", "bot_mode": "polling"}
