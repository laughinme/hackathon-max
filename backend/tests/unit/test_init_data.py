import json
from datetime import UTC, datetime, timedelta

import pytest

from infrastructure.max.init_data import (
    InvalidInitDataError,
    sign_init_data,
    validate_init_data,
)

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)
TOKEN = "bot-token"


def fields(**overrides: str) -> dict[str, str]:
    values = {
        "auth_date": str(int(NOW.timestamp())),
        "chat": json.dumps({"id": -100, "type": "CHAT"}),
        "start_param": "house_psk001",
        "user": json.dumps({"id": 67890, "first_name": "Max"}),
    }
    values.update(overrides)
    return values


def test_valid_signature_is_parsed():
    data = validate_init_data(sign_init_data(fields(), TOKEN), TOKEN, now=NOW)
    assert (data.user_id, data.chat_id, data.start_param) == (
        67890,
        -100,
        "house_psk001",
    )


def test_signature_from_other_bot_is_rejected():
    with pytest.raises(InvalidInitDataError):
        validate_init_data(sign_init_data(fields(), "other"), TOKEN, now=NOW)


def test_tampered_user_is_rejected():
    raw = sign_init_data(fields(), TOKEN).replace("67890", "11111")
    with pytest.raises(InvalidInitDataError):
        validate_init_data(raw, TOKEN, now=NOW)


def test_stale_auth_date_is_rejected():
    raw = sign_init_data(fields(), TOKEN)
    with pytest.raises(InvalidInitDataError):
        validate_init_data(raw, TOKEN, now=NOW + timedelta(hours=2))
