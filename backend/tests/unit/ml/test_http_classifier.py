"""Тесты HTTP-адаптера классификатора: реальные локальные соединения.

Без библиотек-моков httpx/aiohttp (правило ARCHITECTURE.md §2.6) — тут
и не нужно: aiohttp.test_utils поднимает настоящий локальный сервер
для happy path, а недоступный порт даёт настоящую сетевую ошибку для
проверки отката на правила.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from infrastructure.ml.http_classifier import HttpClassifier

UNREACHABLE_URL = "http://127.0.0.1:1"


@asynccontextmanager
async def _running_server(app: web.Application) -> AsyncIterator[str]:
    """Поднимает локальный aiohttp-сервер и отдаёт его base_url."""

    server = TestServer(app)
    await server.start_server()
    try:
        yield str(server.make_url(""))
    finally:
        await server.close()


async def test_falls_back_to_rules_when_service_is_unreachable() -> None:
    classifier = HttpClassifier(base_url=UNREACHABLE_URL, timeout_sec=1.0)

    result = await classifier.classify("не работает лифт, застрял между этажами")

    assert result.category_code == "lift"
    await classifier.close()


async def test_falls_back_to_rules_on_non_200_response() -> None:
    async def classify_handler(_: web.Request) -> web.Response:
        return web.json_response({"detail": "models not ready"}, status=503)

    app = web.Application()
    app.router.add_post("/classify", classify_handler)

    async with _running_server(app) as base_url:
        classifier = HttpClassifier(base_url=base_url, timeout_sec=1.0)

        result = await classifier.classify("течёт кран на кухне")

        assert result.category_code == "water"
        await classifier.close()


async def test_uses_remote_classification_when_service_responds() -> None:
    async def classify_handler(_: web.Request) -> web.Response:
        return web.json_response(
            {
                "category_code": "heating",
                "category_confidence": 0.93,
                "is_emergency": True,
                "emergency_confidence": 0.81,
            }
        )

    app = web.Application()
    app.router.add_post("/classify", classify_handler)

    async with _running_server(app) as base_url:
        classifier = HttpClassifier(base_url=base_url, timeout_sec=1.0)

        result = await classifier.classify("не греют батареи")

        assert result.category_code == "heating"
        assert result.is_emergency is True
        assert result.category_confidence == pytest.approx(0.93)
        await classifier.close()
