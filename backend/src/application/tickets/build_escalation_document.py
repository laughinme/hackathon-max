"""Assemble the complaint to the housing inspection for one ticket."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from application.errors import TicketNotFoundError
from application.ports.clock import Clock
from application.ports.documents import EscalationDocument, EscalationRenderer
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class RenderedDocument:
    filename: str
    content: bytes


class BuildEscalationDocument:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        queries: TicketQueries,
        renderer: EscalationRenderer,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._renderer = renderer
        self._clock = clock

    async def execute(self, ticket_id: UUID) -> RenderedDocument:
        now = self._clock.now()
        view = await self._queries.get(ticket_id, now)
        if view is None:
            raise TicketNotFoundError()
        async with self._uow_factory() as uow:
            company = await uow.housing.get_company(view.company_id)
        if company is None:
            raise TicketNotFoundError()

        document = EscalationDocument(
            ticket=view,
            company_name=company.name,
            company_phone=company.phone,
            region=company.region,
            is_demo=company.is_demo,
            generated_at=now,
        )
        return RenderedDocument(
            filename=f"zhaloba-gzhi-{view.number}.pdf",
            content=self._renderer.render(document),
        )
