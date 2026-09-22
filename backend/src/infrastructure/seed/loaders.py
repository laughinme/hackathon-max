"""Write the demo dataset to PostgreSQL or to the in-memory store (idempotent)."""

from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.db.mappers import ticket_to_row
from infrastructure.db.models import (
    BuildingRow,
    ManagementCompanyRow,
    TicketRow,
)
from infrastructure.memory.tickets import InMemoryStore
from infrastructure.seed.demo_data import DemoDataset


async def load_into_postgres(
    session_factory: async_sessionmaker[AsyncSession], dataset: DemoDataset
) -> bool:
    """Returns False if the demo company already exists (nothing written)."""

    async with session_factory() as session, session.begin():
        if await session.get(ManagementCompanyRow, dataset.company.id) is not None:
            return False
        company = dataset.company
        session.add(
            ManagementCompanyRow(
                id=company.id,
                name=company.name,
                phone=company.phone,
                region=company.region,
                is_demo=company.is_demo,
            )
        )
        await session.flush()  # rows have no ORM relationships: order inserts
        session.add_all(
            BuildingRow(
                id=b.id,
                code=b.code,
                address=b.address,
                company_id=b.company_id,
                is_demo=b.is_demo,
            )
            for b in dataset.buildings
        )
        await session.flush()
        session.add_all(ticket_to_row(ticket) for ticket in dataset.tickets)
        await session.flush()
        # Continue real ticket numbers after the synthetic history.
        highest = await session.scalar(select(func.count()).select_from(TicketRow))
        await session.execute(
            text("SELECT setval('ticket_number_seq', :value)"),
            {"value": max(int(highest or 0), 1)},
        )
    return True


def load_into_memory(store: InMemoryStore, dataset: DemoDataset) -> None:
    store.companies[dataset.company.id] = dataset.company
    store.buildings.update({b.id: b for b in dataset.buildings})
    store.tickets.update({t.id: t for t in dataset.tickets})
    store.sequence = max(store.sequence, len(dataset.tickets))
