"""Webhook signatures: HMAC-SHA256 over "<timestamp>.<raw body>".

The same function is used by the sender, the mock CRM and the examples in
docs/INTEGRATIONS.md, so what we sign and what they check never drift apart.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

SIGNATURE_HEADER = "X-Domovoy-Signature"
TIMESTAMP_HEADER = "X-Domovoy-Timestamp"
EVENT_ID_HEADER = "X-Domovoy-Event-Id"
EVENT_TYPE_HEADER = "X-Domovoy-Event-Type"
#: Receivers should refuse older requests: a replayed body keeps its old stamp.
TOLERANCE_SECONDS = 300


def encode_body(envelope: dict[str, Any]) -> bytes:
    return json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode()


def sign(secret: str, timestamp: int, body: bytes) -> str:
    digest = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return f"sha256={digest}"


def verify(
    secret: str, timestamp: str, body: bytes, signature: str, now: float
) -> bool:
    """For receivers written in Python (the mock CRM uses it)."""

    try:
        stamp = int(timestamp)
    except ValueError:
        return False
    if abs(now - stamp) > TOLERANCE_SECONDS:
        return False
    return hmac.compare_digest(sign(secret, stamp, body), signature.strip())
