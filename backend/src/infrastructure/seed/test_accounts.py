"""Fixed accounts for checkers of the REST API (DATA-API.yaml).

The mini-app signs in with MAX launch data; checkers without MAX get it from
scripts/sign_init_data.py for these ids. The ids are negative like all
synthetic users: the bot never messages them. Idempotent: tickets have fixed
ids and are created only once.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid5

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.ports.clock import Clock
from application.ports.unit_of_work import UnitOfWorkFactory
from application.tickets.registration import NewTicket, register_ticket
from domain.housing.entities import Dispatcher, ResidencyKind, Resident
from domain.tickets.entities import Ticket
from domain.tickets.enums import ActorRole, TicketStatus
from domain.tickets.sla import SlaPolicy
from infrastructure.db.models import TicketRow
from infrastructure.seed.demo_data import NAMESPACE

TEST_RESIDENT_ID = -100
TEST_DISPATCHER_ID = -200
TEST_BUILDING_CODE = "psk001"


@dataclass(frozen=True)
class _Plan:
    key: str
    category: str
    text: str
    age: timedelta
    steps: tuple[TicketStatus, ...]


PLANS = (
    _Plan("open", "cleaning", "Не убирают подъезд неделю, грязно у лифта",
          timedelta(hours=1), ()),
    _Plan("done", "light", "Не горит свет на 3 этаже",
          timedelta(hours=20), (TicketStatus.ACKNOWLEDGED, TicketStatus.DONE)),
    _Plan("overdue", "lift", "Лифт не работает второй день",
          timedelta(days=3), (TicketStatus.ACKNOWLEDGED,)),
)  # fmt: skip


def test_ticket_id(key: str) -> UUID:
    return uuid5(NAMESPACE, f"test-account-ticket-{key}")


async def ensure_test_accounts(uow_factory: UnitOfWorkFactory, clock: Clock) -> int:
    """Returns how many test tickets were created now."""

    now = clock.now()
    sla = SlaPolicy()
    created = 0
    async with uow_factory() as uow:
        company = await uow.housing.get_demo_company()
        building = await uow.housing.get_building_by_code(TEST_BUILDING_CODE)
        if company is None or building is None:
            return 0
        if await uow.housing.get_resident(TEST_RESIDENT_ID) is None:
            await uow.housing.save_resident(
                Resident(TEST_RESIDENT_ID, building.id, ResidencyKind.OWNER, now)
            )
        if await uow.housing.get_dispatcher(TEST_DISPATCHER_ID) is None:
            await uow.housing.save_dispatcher(
                Dispatcher(TEST_DISPATCHER_ID, company.id, now)
            )
        for plan in PLANS:
            if await uow.tickets.get(test_ticket_id(plan.key)) is not None:
                continue
            created_at = now - plan.age
            ticket = await register_ticket(
                uow,
                sla,
                building,
                NewTicket(TEST_RESIDENT_ID, None, plan.category, False, plan.text),
                created_at,
            )
            ticket.id = test_ticket_id(plan.key)
            _replay(ticket, plan, created_at)
            if ticket.is_overdue(now):
                ticket.overdue_notified_at = ticket.deadlines.resolve_by
            await uow.tickets.add(ticket)
            created += 1
        await uow.commit()
    return created


def _replay(ticket: Ticket, plan: _Plan, created_at: datetime) -> None:
    for step, status in enumerate(plan.steps, start=1):
        ticket.change_status(
            status,
            actor_role=ActorRole.DISPATCHER,
            actor_id=TEST_DISPATCHER_ID,
            now=created_at + timedelta(hours=2 * step),
            comment="Мастер назначен" if status is TicketStatus.ACKNOWLEDGED else None,
        )


async def reset_test_tickets(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Drop the test tickets so the next ensure_test_accounts recreates them in
    their initial states (checks in DATA-API.yaml change statuses)."""

    ids = [test_ticket_id(plan.key) for plan in PLANS]
    async with session_factory() as session, session.begin():
        await session.execute(delete(TicketRow).where(TicketRow.id.in_(ids)))
