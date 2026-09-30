"""Send a signed test event right now and report what the system answered."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from application.integrations.payload import SCHEMA_VERSION
from application.ports.clock import Clock
from application.ports.integrations import WebhookSender
from domain.integrations.entities import Integration
from domain.integrations.exceptions import WebhookUrlRejectedError

PING_TYPE = "ping"


@dataclass(frozen=True, slots=True)
class PingResult:
    ok: bool
    status_code: int | None
    error: str | None
    #: What the system would have linked from its answer, if anything.
    answer: dict | None


class PingWebhook:
    def __init__(self, sender: WebhookSender, clock: Clock) -> None:
        self._sender = sender
        self._clock = clock

    async def execute(self, integration: Integration) -> PingResult:
        if not integration.webhook_url or not integration.webhook_secret:
            raise WebhookUrlRejectedError("set the webhook first: PUT /webhook")
        body = {
            "id": str(uuid4()),
            "seq": None,
            "type": PING_TYPE,
            "schema_version": SCHEMA_VERSION,
            "occurred_at": self._clock.now().isoformat(),
            "integration_id": str(integration.id),
            "ticket": None,
            "data": {"message": "Тестовое событие «Домового»: подпись и адрес верны"},
        }
        try:
            response = await self._sender.send(
                integration.webhook_url, integration.webhook_secret, body
            )
        except Exception as exc:  # noqa: BLE001 - reported to the caller as is
            return PingResult(False, None, f"{type(exc).__name__}: {exc}"[:500], None)
        ok = 200 <= response.status_code < 300
        error = None if ok else f"HTTP {response.status_code}"
        return PingResult(ok, response.status_code, error, response.body)
