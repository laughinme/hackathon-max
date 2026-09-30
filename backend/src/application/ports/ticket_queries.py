"""Read side for tickets: lists and cards already joined with building data."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from application.tickets.dto import TicketView


class TicketQueries(Protocol):
    async def get(self, ticket_id: UUID, now: datetime) -> TicketView | None: ...

    async def get_by_number(self, number: str, now: datetime) -> TicketView | None: ...

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

    async def list_for_building(
        self, building_id: UUID, since: datetime, now: datetime
    ) -> list[TicketView]:
        """Tickets of one building created since `since`, newest first."""
        ...

    async def list_changed(
        self,
        company_id: UUID,
        after: tuple[datetime, UUID] | None,
        now: datetime,
        limit: int,
    ) -> list[TicketView]:
        """Tickets of the company by (updated_at, id) strictly after `after`:
        a stable keyset for syncing into an external system."""
        ...
