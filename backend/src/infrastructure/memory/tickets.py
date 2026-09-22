"""In-memory ticket storage for the offline simulator and unit tests.

Implements the same ports as the PostgreSQL adapter. Aggregates are deep-copied
on the way in and out, so uncommitted changes are discarded like in a real
transaction.
"""

from __future__ import annotations

import copy
from types import TracebackType
from typing import Self
from uuid import UUID

from domain.tickets.entities import Ticket


class InMemoryTicketStore:
    def __init__(self) -> None:
        self.tickets: dict[UUID, Ticket] = {}
        self.sequence = 0


class InMemoryTicketRepository:
    def __init__(self, store: InMemoryTicketStore) -> None:
        self._store = store
        self.pending: dict[UUID, Ticket] = {}

    async def next_sequence(self) -> int:
        self._store.sequence += 1
        return self._store.sequence

    async def add(self, ticket: Ticket) -> None:
        self.pending[ticket.id] = copy.deepcopy(ticket)

    async def get(self, ticket_id: UUID) -> Ticket | None:
        ticket = self._store.tickets.get(ticket_id)
        return copy.deepcopy(ticket) if ticket is not None else None

    async def save(self, ticket: Ticket) -> None:
        if ticket.id not in self._store.tickets:
            raise LookupError(f"Ticket {ticket.id} is not persisted")
        self.pending[ticket.id] = copy.deepcopy(ticket)

    async def list_by_reporter(self, reporter_id: int) -> list[Ticket]:
        tickets = [
            copy.deepcopy(ticket)
            for ticket in self._store.tickets.values()
            if ticket.reporter_id == reporter_id
        ]
        return sorted(tickets, key=lambda ticket: ticket.created_at, reverse=True)


class InMemoryUnitOfWork:
    tickets: InMemoryTicketRepository

    def __init__(self, store: InMemoryTicketStore) -> None:
        self._store = store

    async def __aenter__(self) -> Self:
        self.tickets = InMemoryTicketRepository(self._store)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.tickets.pending.clear()

    async def commit(self) -> None:
        self._store.tickets.update(self.tickets.pending)
        self.tickets.pending.clear()
