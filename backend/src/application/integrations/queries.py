"""Read side of the integration API: the connection, its tickets and events."""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from uuid import UUID

from application.integrations.dto import (
    EventPage,
    IntegrationView,
    LinkedTicket,
    TicketPage,
    to_integration_view,
)
from application.integrations.payload import envelope
from application.integrations.ticket_refs import load_company_ticket
from application.ports.clock import Clock
from application.ports.integrations import IntegrationFeed
from application.ports.ticket_queries import TicketQueries
from application.ports.unit_of_work import UnitOfWorkFactory
from domain.errors import DomainError
from domain.housing.exceptions import NotADispatcherError
from domain.integrations.entities import Integration

MAX_PAGE = 200


class InvalidCursorError(DomainError):
    code = "invalid_cursor"

    def __init__(self) -> None:
        super().__init__("Invalid cursor: pass back next_cursor as it was returned")


def encode_cursor(updated_at: datetime, ticket_id: UUID) -> str:
    raw = f"{updated_at.isoformat()}|{ticket_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        at, ticket_id = raw.split("|")
        return datetime.fromisoformat(at), UUID(ticket_id)
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise InvalidCursorError() from None


async def pending_events(feed: IntegrationFeed, integration: Integration) -> int:
    if integration.webhook_url is None:
        return 0
    return await feed.pending_count(integration.company_id, integration.delivered_seq)


class DescribeIntegration:
    def __init__(self, feed: IntegrationFeed) -> None:
        self._feed = feed

    async def execute(self, integration: Integration) -> IntegrationView:
        return to_integration_view(
            integration, await pending_events(self._feed, integration)
        )


class ListCompanyIntegrations:
    """For the dispatcher's screen: every connection of their company."""

    def __init__(self, uow_factory: UnitOfWorkFactory, feed: IntegrationFeed) -> None:
        self._uow_factory = uow_factory
        self._feed = feed

    async def execute(self, dispatcher_id: int) -> list[IntegrationView]:
        async with self._uow_factory() as uow:
            dispatcher = await uow.housing.get_dispatcher(dispatcher_id)
            if dispatcher is None:
                raise NotADispatcherError()
            found = await uow.integrations.list_for_company(dispatcher.company_id)
        return [
            to_integration_view(item, await pending_events(self._feed, item))
            for item in found
        ]


class GetIntegrationTicket:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        queries: TicketQueries,
        clock: Clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._queries = queries
        self._clock = clock

    async def execute(self, integration: Integration, ref: str) -> LinkedTicket:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            ticket = await load_company_ticket(
                ref, integration, uow, self._queries, now
            )
            link = await uow.integrations.get_link(integration.id, ticket.id)
        view = await self._queries.get(ticket.id, now)
        assert view is not None
        return LinkedTicket(view, link)


class ListChangedTickets:
    """Initial import and reconciliation: every ticket, in the order of last
    change; a page boundary never skips or repeats a ticket."""

    def __init__(
        self, queries: TicketQueries, feed: IntegrationFeed, clock: Clock
    ) -> None:
        self._queries = queries
        self._feed = feed
        self._clock = clock

    async def execute(
        self, integration: Integration, cursor: str | None, limit: int
    ) -> TicketPage:
        limit = max(1, min(limit, MAX_PAGE))
        after = decode_cursor(cursor) if cursor else None
        views = await self._queries.list_changed(
            integration.company_id, after, self._clock.now(), limit
        )
        links = await self._feed.links_for(integration.id, [v.id for v in views])
        last = views[-1] if views else None
        return TicketPage(
            tickets=tuple(LinkedTicket(v, links.get(v.id)) for v in views),
            next_cursor=encode_cursor(last.updated_at, last.id)
            if last is not None and len(views) == limit
            else None,
        )


class ListIntegrationEvents:
    """The pull alternative to webhooks, for systems that cannot receive HTTP
    (1C behind NAT, a nightly job): the same envelopes, by cursor."""

    def __init__(self, feed: IntegrationFeed) -> None:
        self._feed = feed

    async def execute(
        self, integration: Integration, after: int, limit: int
    ) -> EventPage:
        limit = max(1, min(limit, MAX_PAGE))
        events = await self._feed.events_after(integration.company_id, after, limit)
        links = await self._feed.links_for(
            integration.id, list({event.ticket_id for event in events})
        )
        return EventPage(
            events=tuple(
                envelope(event, integration, links.get(event.ticket_id))
                for event in events
                if integration.wants(event)
            ),
            next_after=(events[-1].seq or after) if events else after,
            has_more=len(events) == limit,
        )
