"""Signed webhook POSTs over aiohttp, never into our own network.

The URL comes from outside (the connected system), so it must not become a
way to reach internal services (SSRF): HTTPS only, and every address the
host resolves to is checked at connection time, which also covers DNS
rebinding. Redirects are not followed. `allow_private=True` lifts both for
local development with the mock CRM.
"""

from __future__ import annotations

import ipaddress
import json
import socket
import time
from typing import Any
from urllib.parse import urlsplit

import aiohttp
from aiohttp.abc import ResolveResult

from application.ports.integrations import WebhookResponse
from domain.integrations.exceptions import WebhookUrlRejectedError
from infrastructure.integrations.signature import (
    EVENT_ID_HEADER,
    EVENT_TYPE_HEADER,
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    encode_body,
    sign,
)

TIMEOUT_SECONDS = 10.0
MAX_ANSWER_BYTES = 64 * 1024
USER_AGENT = "Domovoy-Webhooks/1"


def is_public_address(host: str) -> bool:
    address = ipaddress.ip_address(host.split("%", 1)[0])
    return address.is_global and not address.is_multicast


class _PublicOnlyResolver(aiohttp.ThreadedResolver):
    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> list[ResolveResult]:
        results = await super().resolve(host, port, family)
        if not results or not all(is_public_address(r["host"]) for r in results):
            raise OSError(f"{host} resolves to a non-public address")
        return results


class AiohttpWebhookSender:
    def __init__(self, *, allow_private: bool = False) -> None:
        self._allow_private = allow_private
        self._session: aiohttp.ClientSession | None = None

    def check_url(self, url: str) -> None:
        parts = urlsplit(url)
        schemes = ("https", "http") if self._allow_private else ("https",)
        if parts.scheme not in schemes or not parts.hostname:
            raise WebhookUrlRejectedError("an absolute https:// URL is required")
        if len(url) > 2048:
            raise WebhookUrlRejectedError("the URL is longer than 2048 characters")
        if self._allow_private:
            return
        host = parts.hostname
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise WebhookUrlRejectedError("internal host names are not allowed")
        try:
            literal = is_public_address(host)
        except ValueError:
            return  # a host name: checked on every connection by the resolver
        if not literal:
            raise WebhookUrlRejectedError("private and local addresses are not allowed")

    async def send(
        self, url: str, secret: str, envelope: dict[str, Any]
    ) -> WebhookResponse:
        self.check_url(url)
        body = encode_body(envelope)
        timestamp = int(time.time())
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": USER_AGENT,
            TIMESTAMP_HEADER: str(timestamp),
            SIGNATURE_HEADER: sign(secret, timestamp, body),
            EVENT_ID_HEADER: str(envelope.get("id", "")),
            EVENT_TYPE_HEADER: str(envelope.get("type", "")),
        }
        async with self._client().post(
            url, data=body, headers=headers, allow_redirects=False
        ) as response:
            raw = await response.content.read(MAX_ANSWER_BYTES)
            return WebhookResponse(response.status, _json_object(raw))

    def _client(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                resolver=None if self._allow_private else _PublicOnlyResolver(),
                limit=20,
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS),
            )
        return self._session

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()


def _json_object(raw: bytes) -> dict[str, Any] | None:
    try:
        value = json.loads(raw.decode("utf-8")) if raw.strip() else None
    except (UnicodeDecodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None
