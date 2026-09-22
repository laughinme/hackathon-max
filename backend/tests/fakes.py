"""Test doubles and an in-memory world shared by unit tests."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.config import Config
from app.services import Services, build_services
from application.ports.classifier import Classification
from domain.housing.entities import Building, Dispatcher, ManagementCompany
from domain.notifications.entities import Notification
from infrastructure.memory.tickets import (
    InMemoryStore,
    InMemoryTicketQueries,
    InMemoryUnitOfWork,
)

BOT_TOKEN = "test-bot-token"


class FixedClock:
    def __init__(self, now: datetime | None = None) -> None:
        self.current = now or datetime(2026, 9, 23, 9, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class StaticClassifier:
    def __init__(self, classification: Classification) -> None:
        self.classification = classification

    async def classify(self, text: str) -> Classification:
        return self.classification


class RecordingSender:
    def __init__(self, fail_times: int = 0) -> None:
        self.sent: list[Notification] = []
        self.fail_times = fail_times

    async def send(self, notification: Notification) -> None:
        if self.fail_times:
            self.fail_times -= 1
            raise ConnectionError("MAX is down")
        self.sent.append(notification)


def classification(
    category: str = "lift",
    *,
    is_emergency: bool = False,
    emergency_confidence: float = 0.9,
) -> Classification:
    return Classification(
        category_code=category,
        category_confidence=0.9,
        is_emergency=is_emergency,
        emergency_confidence=emergency_confidence,
    )


CONFIG = Config(
    bot_token=BOT_TOKEN,
    log_level="INFO",
    database_url="postgresql+asyncpg://user:pass@localhost:1/unused",
    bot_mode="polling",
    webhook_url=None,
    webhook_secret=None,
    http_host="127.0.0.1",
    http_port=8080,
    polling_takeover=False,
    demo_mode=True,
    dev_auth_enabled=False,
    llm_enabled=False,
    llm_base_url="",
    llm_model="",
    llm_api_key=None,
    llm_timeout_sec=1.0,
    llm_temperature=0.0,
    ml_service_url="http://localhost:1",
    ml_service_timeout_sec=0.1,
    ml_confidence_threshold=0.6,
)


@dataclass
class World:
    """In-memory store with one company and two buildings."""

    store: InMemoryStore
    clock: FixedClock
    company: ManagementCompany
    building: Building
    other_building: Building
    services: Services

    def uow(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(self.store)

    def add_dispatcher(self, max_user_id: int) -> None:
        self.store.dispatchers[max_user_id] = Dispatcher(
            max_user_id=max_user_id,
            company_id=self.company.id,
            joined_at=self.clock.now(),
        )


def make_world(**config_overrides: object) -> World:
    store = InMemoryStore()
    clock = FixedClock()
    company = ManagementCompany(
        id=uuid4(), name="УО Тест", phone="+7 000", region="Псков", is_demo=True
    )
    building = Building(uuid4(), "psk001", "ул. Тестовая, 1", company.id, True)
    other = Building(uuid4(), "psk002", "ул. Тестовая, 2", company.id, True)
    store.companies[company.id] = company
    store.buildings.update({building.id: building, other.id: other})
    services = build_services(
        replace(CONFIG, **config_overrides),  # type: ignore[arg-type]
        uow_factory=lambda: InMemoryUnitOfWork(store),
        queries=InMemoryTicketQueries(store),
        clock=clock,
        classifier=StaticClassifier(classification()),
    )
    return World(store, clock, company, building, other, services)
