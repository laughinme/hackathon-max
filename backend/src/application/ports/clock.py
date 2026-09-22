"""Time source port: use cases never call `datetime.now()` directly."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current timezone-aware time."""
        ...
