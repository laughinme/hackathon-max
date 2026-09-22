"""One business transaction across all write-side repositories."""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self

from application.ports.housing import HousingRepository
from application.ports.outbox import Outbox
from application.ports.tickets import TicketRepository


class UnitOfWork(Protocol):
    """Rolls back unless `commit()` was called."""

    @property
    def tickets(self) -> TicketRepository: ...

    @property
    def housing(self) -> HousingRepository: ...

    @property
    def outbox(self) -> Outbox: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
