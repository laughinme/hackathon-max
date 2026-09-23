"""Read side for tickets: lists and cards already joined with building data."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from application.tickets.dto import TicketView


class TicketQueries(Protocol):
    async def get(self, ticket_id: UUID, now: datetime) -> TicketView | None: ...

    async def list_for_reporter(
        self, reporter_id: int, now: datetime
    ) -> list[TicketView]: ...

    async def list_for_company(
        self, company_id: UUID, now: datetime, *, open_only: bool, limit: int
    ) -> list[TicketView]:
        """Open tickets first, ordered by the resolution deadline."""
        ...

    async def find_open_duplicate(
        self, building_id: UUID, category_code: str, since: datetime, now: datetime
    ) -> TicketView | None:
        """The newest open ticket of this building and category since `since`."""
        ...
