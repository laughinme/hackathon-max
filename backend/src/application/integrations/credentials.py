"""API keys and webhook secrets: shown once, stored as a hash (keys) or used to
sign (secrets)."""

from __future__ import annotations

import hashlib
import secrets

KEY_PREFIX = "dmv_"
SECRET_PREFIX = "whsec_"
#: Characters of the key kept in clear to tell keys apart ("dmv_AbC1…").
VISIBLE_PREFIX_LENGTH = 8


def new_api_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def new_webhook_secret() -> str:
    return SECRET_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """A random 256-bit key needs no slow hash: SHA-256 cannot be brute-forced."""

    return hashlib.sha256(key.strip().encode()).hexdigest()


def visible_prefix(key: str) -> str:
    return key[:VISIBLE_PREFIX_LENGTH]
