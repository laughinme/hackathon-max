"""Idempotent webhook intake: MAX redelivers an update it thinks was lost."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Inbox(Protocol):
    async def register(self, key: str, now: datetime) -> bool:
        """True the first time a key is seen, False for a redelivery."""
        ...

    async def purge(self, older_than: datetime) -> int: ...
