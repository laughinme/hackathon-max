"""In-memory adapters of the persistence ports, for the simulator and unit tests.

Aggregates are deep-copied on the way in and out and changes are applied only
on commit, so they behave like a real transaction.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from types import TracebackType
from typing import Any, Self
from uuid import UUID

from application.ports.outbox import PendingNotification
from application.tickets.dto import TicketView, to_view
from domain.chats.entities import ChatHint, HouseChat
from domain.housing.entities import (
    Building,
    Dispatcher,
    ManagementCompany,
    Resident,
)
from domain.notifications.entities import Notification
from domain.tickets.entities import ANONYMOUS_REPORTER, Ticket


@dataclass
class OutboxEntry:
    notification: Notification
    next_attempt_at: datetime | None
    attempts: int = 0
    sent_at: datetime | None = None
    last_error: str | None = None


@dataclass
class InMemoryStore:
    tickets: dict[UUID, Ticket] = field(default_factory=dict)
    sequence: int = 0
    companies: dict[UUID, ManagementCompany] = field(default_factory=dict)
    buildings: dict[UUID, Building] = field(default_factory=dict)
    residents: dict[int, Resident] = field(default_factory=dict)
    dispatchers: dict[int, Dispatcher] = field(default_factory=dict)
    outbox: dict[UUID, OutboxEntry] = field(default_factory=dict)
    chats: dict[int, HouseChat] = field(default_factory=dict)
    hints: dict[UUID, ChatHint] = field(default_factory=dict)


_DELETED = object()


class _Pending:
    def __init__(self) -> None:
        self.writes: list[tuple[str, Any, Any]] = []

    def put(self, table: str, key: Any, value: Any) -> None:
        self.writes.append((table, key, copy.deepcopy(value)))

    def drop(self, table: str, key: Any) -> None:
        self.writes.append((table, key, _DELETED))


class InMemoryTicketRepository:
    def __init__(self, store: InMemoryStore, pending: _Pending) -> None:
        self._store = store
        self._pending = pending

    async def next_sequence(self) -> int:
        self._store.sequence += 1  # like a DB sequence: not rolled back
        return self._store.sequence

    async def add(self, ticket: Ticket) -> None:
        self._pending.put("tickets", ticket.id, ticket)

    async def get(self, ticket_id: UUID) -> Ticket | None:
        ticket = self._store.tickets.get(ticket_id)
        return copy.deepcopy(ticket) if ticket else None

    async def save(self, ticket: Ticket) -> None:
        if ticket.id not in self._store.tickets:
            raise LookupError(f"Ticket {ticket.id} is not persisted")
        self._pending.put("tickets", ticket.id, ticket)

    async def detach_reporter(self, reporter_id: int) -> int:
        mine = [t for t in self._store.tickets.values() if t.reporter_id == reporter_id]
        for ticket in mine:
            detached = copy.deepcopy(ticket)
            detached.reporter_id = ANONYMOUS_REPORTER
            self._pending.put("tickets", ticket.id, detached)
        return len(mine)

    async def list_overdue_unnotified(self, now: datetime, limit: int) -> list[Ticket]:
        due = [
            t
            for t in self._store.tickets.values()
            if t.is_overdue(now) and t.overdue_notified_at is None
        ]
        due.sort(key=lambda t: t.deadlines.resolve_by)
        return [copy.deepcopy(t) for t in due[:limit]]


class InMemoryHousingRepository:
    def __init__(self, store: InMemoryStore, pending: _Pending) -> None:
        self._store = store
        self._pending = pending

    async def get_building(self, building_id: UUID) -> Building | None:
        return self._store.buildings.get(building_id)

    async def get_building_by_code(self, code: str) -> Building | None:
        return next((b for b in self._store.buildings.values() if b.code == code), None)

    async def list_demo_buildings(self, limit: int) -> list[Building]:
        demo = sorted(
            (b for b in self._store.buildings.values() if b.is_demo),
            key=lambda b: b.code,
        )
        return demo[:limit]

    async def get_company(self, company_id: UUID) -> ManagementCompany | None:
        return self._store.companies.get(company_id)

    async def get_demo_company(self) -> ManagementCompany | None:
        return next((c for c in self._store.companies.values() if c.is_demo), None)

    async def get_resident(self, max_user_id: int) -> Resident | None:
        resident = self._store.residents.get(max_user_id)
        return copy.deepcopy(resident) if resident else None

    async def save_resident(self, resident: Resident) -> None:
        self._pending.put("residents", resident.max_user_id, resident)

    async def get_dispatcher(self, max_user_id: int) -> Dispatcher | None:
        return self._store.dispatchers.get(max_user_id)

    async def save_dispatcher(self, dispatcher: Dispatcher) -> None:
        self._pending.put("dispatchers", dispatcher.max_user_id, dispatcher)

    async def delete_resident(self, max_user_id: int) -> None:
        self._pending.drop("residents", max_user_id)

    async def delete_dispatcher(self, max_user_id: int) -> None:
        self._pending.drop("dispatchers", max_user_id)

    async def list_dispatchers(self, company_id: UUID) -> list[Dispatcher]:
        found = [
            d for d in self._store.dispatchers.values() if d.company_id == company_id
        ]
        return sorted(found, key=lambda d: d.joined_at)


class InMemoryChatRepository:
    def __init__(self, store: InMemoryStore, pending: _Pending) -> None:
        self._store = store
        self._pending = pending

    async def get(self, chat_id: int) -> HouseChat | None:
        chat = self._store.chats.get(chat_id)
        return copy.deepcopy(chat) if chat else None

    async def save(self, chat: HouseChat) -> None:
        self._pending.put("chats", chat.chat_id, chat)

    async def add_hint(self, hint: ChatHint) -> None:
        self._pending.put("hints", hint.id, hint)

    async def get_hint(self, hint_id: UUID) -> ChatHint | None:
        hint = self._store.hints.get(hint_id)
        return copy.deepcopy(hint) if hint else None

    async def save_hint(self, hint: ChatHint) -> None:
        self._pending.put("hints", hint.id, hint)


class InMemoryOutbox:
    def __init__(self, pending: _Pending) -> None:
        self._pending = pending

    async def add(self, notification: Notification) -> None:
        entry = OutboxEntry(notification, next_attempt_at=notification.created_at)
        self._pending.put("outbox", notification.id, entry)


class InMemoryUnitOfWork:
    tickets: InMemoryTicketRepository
    housing: InMemoryHousingRepository
    outbox: InMemoryOutbox
    chats: InMemoryChatRepository

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store
        self._pending = _Pending()

    async def __aenter__(self) -> Self:
        self._pending = _Pending()
        self.tickets = InMemoryTicketRepository(self._store, self._pending)
        self.housing = InMemoryHousingRepository(self._store, self._pending)
        self.outbox = InMemoryOutbox(self._pending)
        self.chats = InMemoryChatRepository(self._store, self._pending)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._pending.writes.clear()

    async def commit(self) -> None:
        for table, key, value in self._pending.writes:
            if value is _DELETED:
                getattr(self._store, table).pop(key, None)
            else:
                getattr(self._store, table)[key] = value
        self._pending.writes.clear()


class InMemoryTicketQueries:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def _view(self, ticket: Ticket, now: datetime) -> TicketView:
        building = self._store.buildings[ticket.building_id]
        return to_view(copy.deepcopy(ticket), now, building.address)

    async def get(self, ticket_id: UUID, now: datetime) -> TicketView | None:
        ticket = self._store.tickets.get(ticket_id)
        return self._view(ticket, now) if ticket else None

    async def list_for_reporter(
        self, reporter_id: int, now: datetime
    ) -> list[TicketView]:
        tickets = [
            t for t in self._store.tickets.values() if t.reporter_id == reporter_id
        ]
        tickets.sort(key=lambda t: t.created_at, reverse=True)
        return [self._view(t, now) for t in tickets]

    async def list_for_company(
        self, company_id: UUID, now: datetime, *, open_only: bool, limit: int
    ) -> list[TicketView]:
        tickets = [
            t
            for t in self._store.tickets.values()
            if t.company_id == company_id and (t.is_open or not open_only)
        ]
        tickets.sort(key=lambda t: (not t.is_open, t.deadlines.resolve_by))
        return [self._view(t, now) for t in tickets[:limit]]

    async def find_open_duplicate(
        self, building_id: UUID, category_code: str, since: datetime, now: datetime
    ) -> TicketView | None:
        found = [
            t
            for t in self._store.tickets.values()
            if t.building_id == building_id
            and t.category_code == category_code
            and t.is_open
            and t.created_at >= since
        ]
        found.sort(key=lambda t: t.created_at, reverse=True)
        return self._view(found[0], now) if found else None


class InMemoryOutboxReader:
    LEASE = timedelta(minutes=2)

    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def claim_batch(self, limit: int, now: datetime) -> list[PendingNotification]:
        due = [
            entry
            for entry in self._store.outbox.values()
            if entry.sent_at is None
            and entry.next_attempt_at is not None
            and entry.next_attempt_at <= now
        ]
        due.sort(key=lambda entry: entry.notification.created_at)
        claimed = []
        for entry in due[:limit]:
            entry.next_attempt_at = now + self.LEASE
            claimed.append(
                PendingNotification(replace(entry.notification), entry.attempts)
            )
        return claimed

    async def mark_sent(self, notification_id: UUID, now: datetime) -> None:
        entry = self._store.outbox[notification_id]
        entry.sent_at, entry.next_attempt_at = now, None

    async def mark_failed(
        self, notification_id: UUID, error: str, retry_at: datetime | None
    ) -> None:
        entry = self._store.outbox[notification_id]
        entry.attempts += 1
        entry.last_error = error
        entry.next_attempt_at = retry_at


class InMemoryInbox:
    def __init__(self) -> None:
        self.keys: dict[str, datetime] = {}

    async def register(self, key: str, now: datetime) -> bool:
        if key in self.keys:
            return False
        self.keys[key] = now
        return True

    async def purge(self, older_than: datetime) -> int:
        old = [key for key, at in self.keys.items() if at < older_than]
        for key in old:
            del self.keys[key]
        return len(old)
