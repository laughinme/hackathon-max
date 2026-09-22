"""Validation of MAX mini-app launch data (`WebApp.initData`).

Algorithm: dev.max.ru/docs/webapps/validation (local copy in
docs/max/reference/platform/webapps/validation.md).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl

from domain.errors import DomainError


class InvalidInitDataError(DomainError):
    code = "invalid_init_data"

    def __init__(self, reason: str) -> None:
        super().__init__(f"Mini-app launch data is invalid: {reason}")


@dataclass(frozen=True, slots=True)
class InitData:
    user_id: int
    first_name: str
    auth_date: datetime
    chat_id: int | None
    start_param: str | None


def validate_init_data(
    raw: str, bot_token: str, *, now: datetime, max_age_seconds: int = 3600
) -> InitData:
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise InvalidInitDataError("malformed query string") from exc

    keys = [key for key, _ in pairs]
    if keys.count("hash") != 1 or len(keys) != len(set(keys)):
        raise InvalidInitDataError("hash missing or keys duplicated")

    data = dict(pairs)
    received = data.pop("hash")
    launch_params = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, launch_params.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise InvalidInitDataError("signature mismatch")

    try:
        auth_date = datetime.fromtimestamp(int(data["auth_date"]), tz=now.tzinfo)
        user = json.loads(data["user"])
        chat = json.loads(data["chat"]) if data.get("chat") else None
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidInitDataError("required fields missing") from exc

    if (now - auth_date).total_seconds() > max_age_seconds:
        raise InvalidInitDataError("expired")

    return InitData(
        user_id=int(user["id"]),
        first_name=str(user.get("first_name") or ""),
        auth_date=auth_date,
        chat_id=int(chat["id"]) if chat and chat.get("id") is not None else None,
        start_param=data.get("start_param"),
    )


def sign_init_data(fields: dict[str, str], bot_token: str) -> str:
    """Produce a valid initData string (tests and local frontend development)."""

    from urllib.parse import urlencode

    launch_params = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, launch_params.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": signature})
