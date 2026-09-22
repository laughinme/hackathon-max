"""Deterministic synthetic dataset for the demo (DECISIONS Q-10).

Everything here is test data and is marked as such in the bot: one management
company in Pskov, 50 buildings with made-up house numbers, historic tickets
from synthetic residents. Synthetic user ids are negative so they can never
collide with real MAX users and never receive messages.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid5

from domain.housing.entities import Building, ManagementCompany
from domain.tickets.entities import Ticket
from domain.tickets.enums import ActorRole, TicketStatus
from domain.tickets.responsibility import responsibility_for
from domain.tickets.sla import SlaPolicy

NAMESPACE = UUID("6f1c3e2a-8d4b-4f5e-9a1b-2c3d4e5f6a7b")
SYNTHETIC_DISPATCHER_ID = -1
DEMO_BUILDINGS_FOR_ONBOARDING = 3

STREETS = (
    "Октябрьский пр-т", "ул. Гагарина", "Рижский пр-т", "ул. Труда",
    "ул. Юбилейная", "ул. Народная", "ул. Коммунальная", "ул. Кузбасской дивизии",
    "ул. Звёздная", "ул. Индустриальная",
)  # fmt: skip

COMPLAINTS: dict[str, tuple[str, ...]] = {
    "lift": ("Лифт не работает второй день", "Лифт застревает между этажами"),
    "water": ("Течёт стояк в туалете", "Капает с потолка в подъезде"),
    "heating": ("Холодные батареи в квартире", "Не прогревается стояк отопления"),
    "light": ("Не горит свет на лестничной клетке", "Перегорели лампы у лифта"),
    "door": ("Не закрывается входная дверь", "Сломан домофон"),
    "cleaning": ("Не убирают подъезд неделю", "Переполнены контейнеры у дома"),
}
EMERGENCIES = ("Прорвало трубу в подвале, топит", "Искрит электрощиток на этаже")


@dataclass(frozen=True)
class DemoDataset:
    company: ManagementCompany
    buildings: list[Building]
    tickets: list[Ticket]


def _id(name: str) -> UUID:
    return uuid5(NAMESPACE, name)


def build_demo_dataset(now: datetime, *, tickets_count: int = 120) -> DemoDataset:
    rng = random.Random(42)
    company = ManagementCompany(
        id=_id("company"),
        name="УО «Комфорт» (демо)",
        phone="+7 (8112) 00-00-00",
        region="Псковская область",
        is_demo=True,
    )
    buildings = [
        Building(
            id=_id(f"building-{n}"),
            code=f"psk{n:03d}",
            address=f"г. Псков, {STREETS[n % len(STREETS)]}, д. {100 + n} (демо)",
            company_id=company.id,
            is_demo=True,
        )
        for n in range(1, 51)
    ]
    sla = SlaPolicy()
    tickets = [
        _ticket(rng, sla, now, sequence, rng.choice(buildings), company.id)
        for sequence in range(1, tickets_count + 1)
    ]
    return DemoDataset(company, buildings, tickets)


def _ticket(
    rng: random.Random,
    sla: SlaPolicy,
    now: datetime,
    sequence: int,
    building: Building,
    company_id: UUID,
) -> Ticket:
    is_emergency = rng.random() < 0.08
    category = "water" if is_emergency else rng.choice(list(COMPLAINTS))
    text = rng.choice(EMERGENCIES if is_emergency else COMPLAINTS[category])
    recent = rng.random() < 0.3
    created = now - timedelta(
        hours=rng.randint(1, 72) if recent else rng.randint(72, 60 * 24)
    )
    ticket = Ticket.register(
        sequence=sequence,
        building_id=building.id,
        company_id=company_id,
        reporter_id=-(1000 + rng.randint(1, 300)),
        chat_id=None,
        category_code=category,
        is_emergency=is_emergency,
        description=f"{text}. Подъезд {rng.randint(1, 6)}.",
        responsibility=responsibility_for(category),
        deadlines=sla.deadlines(category, is_emergency, created),
        now=created,
    )
    ticket.id = _id(f"ticket-{sequence}")
    _advance(rng, ticket, now)
    return ticket


def _advance(rng: random.Random, ticket: Ticket, now: datetime) -> None:
    """Replay a plausible history: fresh tickets are in the queue, old ones closed."""

    age = now - ticket.created_at
    if age < timedelta(hours=12):
        progress = rng.choice((0, 0, 1))
    elif age < timedelta(days=3):
        progress = rng.choice((1, 2, 2, 3))
    else:
        progress = 3
    steps = (TicketStatus.ACKNOWLEDGED, TicketStatus.IN_PROGRESS, TicketStatus.DONE)
    moment = ticket.created_at
    for status in steps[:progress]:
        moment = min(now, moment + timedelta(hours=rng.randint(1, 20)))
        ticket.change_status(
            status,
            actor_role=ActorRole.DISPATCHER,
            actor_id=SYNTHETIC_DISPATCHER_ID,
            now=moment,
            comment="Мастер назначен" if status is TicketStatus.IN_PROGRESS else None,
        )
    if ticket.status is TicketStatus.DONE and rng.random() < 0.85:
        ticket.change_status(
            TicketStatus.CONFIRMED,
            actor_role=ActorRole.RESIDENT,
            actor_id=ticket.reporter_id,
            now=min(now, moment + timedelta(hours=rng.randint(1, 12))),
        )
