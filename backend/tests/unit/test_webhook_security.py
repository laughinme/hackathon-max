"""Webhook signatures and the SSRF guard on webhook URLs."""

from __future__ import annotations

import pytest

from domain.integrations.exceptions import WebhookUrlRejectedError
from infrastructure.integrations.signature import encode_body, sign, verify
from infrastructure.integrations.webhook_sender import AiohttpWebhookSender

SECRET = "whsec_test"


def test_signature_round_trip_and_tampering():
    body = encode_body({"id": "e1", "ticket": {"description": "Лифт"}})
    signature = sign(SECRET, 1_790_000_000, body)
    assert signature.startswith("sha256=")
    assert verify(SECRET, "1790000000", body, signature, now=1_790_000_100)
    assert not verify(SECRET, "1790000000", body + b" ", signature, now=1_790_000_100)
    assert not verify("whsec_other", "1790000000", body, signature, 1_790_000_100)
    # A replayed request keeps its old timestamp and is refused.
    assert not verify(SECRET, "1790000000", body, signature, now=1_790_001_000)


def test_body_is_compact_utf8_json():
    assert encode_body({"a": "Лифт"}) == '{"a":"Лифт"}'.encode()


@pytest.mark.parametrize(
    "url",
    [
        "http://crm.example.ru/hook",
        "ftp://crm.example.ru/hook",
        "https://localhost/hook",
        "https://127.0.0.1/hook",
        "https://10.1.2.3/hook",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/hook",
        "https://db.internal/hook",
        "not a url",
    ],
)
def test_private_and_plain_http_urls_are_refused(url):
    with pytest.raises(WebhookUrlRejectedError):
        AiohttpWebhookSender().check_url(url)


def test_public_https_is_allowed_and_dev_mode_allows_localhost():
    AiohttpWebhookSender().check_url("https://crm.example.ru/hooks/domovoy")
    AiohttpWebhookSender().check_url("https://8.8.8.8/hook")
    AiohttpWebhookSender(allow_private=True).check_url("http://localhost:8200/hook")
