"""Persistence ports for the ticket aggregate."""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from domain.tickets.entities import Ticket


class TicketRepository(Protocol):
    """Loads and stores whole ticket aggregates (domain objects, never ORM rows)."""

    async def next_sequence(self) -> int: ...

    async def add(self, ticket: Ticket) -> None: ...

    async def get(self, ticket_id: UUID) -> Ticket | None: ...

    async def save(self, ticket: Ticket) -> None: ...

    async def list_by_reporter(self, reporter_id: int) -> list[Ticket]: ...


class UnitOfWork(Protocol):
    """One business transaction. Rolls back unless `commit()` was called."""

    @property
    def tickets(self) -> TicketRepository: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
