"""Write-side persistence port for the ticket aggregate."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from domain.tickets.entities import Ticket


class TicketRepository(Protocol):
    """Loads and stores whole ticket aggregates (domain objects, never ORM rows)."""

    async def next_sequence(self) -> int: ...

    async def add(self, ticket: Ticket) -> None: ...

    async def get(self, ticket_id: UUID) -> Ticket | None: ...

    async def save(self, ticket: Ticket) -> None: ...
