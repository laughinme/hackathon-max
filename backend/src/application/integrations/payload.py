"""The canonical JSON shape of a ticket and of an event for external systems.

One shape for webhooks, the event feed and the REST API, so a system parses
tickets the same way wherever they come from. No MAX user ids: the company
needs the problem, not the resident's account (docs/INTEGRATIONS.md §7).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from application.tickets.dto import TicketView
from domain.integrations.entities import ExternalLink, Integration, IntegrationEvent
from domain.tickets.catalog import get_category
from domain.tickets.enums import TicketStatus

SCHEMA_VERSION = 1


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def ticket_snapshot(view: TicketView) -> dict[str, Any]:
    return {
        "id": str(view.id),
        "number": view.number,
        "status": view.status.value,
        "category": {
            "code": view.category_code,
            "title": get_category(view.category_code).title,
        },
        "is_emergency": view.is_emergency,
        "description": view.description,
        "building": {"id": str(view.building_id), "address": view.building_address},
        "responsible_party": view.responsible_party.value,
        "responsibility_basis": view.responsibility_basis,
        "deadlines": {
            "react_by": _iso(view.react_by),
            "resolve_by": _iso(view.resolve_by),
            "legal_basis": view.deadline_basis,
        },
        "is_overdue": view.is_overdue,
        "source": "house_chat" if view.chat_card_mid is not None else "max_bot",
        "supporters_count": view.supporters_count,
        "photo_urls": [photo.url for photo in view.photos],
        "escalated_at": _iso(view.escalated_at),
        "created_at": _iso(view.created_at),
        "updated_at": _iso(view.updated_at),
        "timeline": [
            {
                "status": event.status.value,
                "actor": event.actor_role.value,
                "at": _iso(event.at),
                "comment": event.comment,
            }
            for event in view.events
        ],
    }


def link_json(link: ExternalLink | None) -> dict[str, Any] | None:
    if link is None:
        return None
    return {
        "id": link.external_id,
        "number": link.external_number,
        "url": link.external_url,
        "status": link.external_status,
    }


def for_integration(
    ticket: dict[str, Any], integration: Integration, link: ExternalLink | None
) -> dict[str, Any]:
    """The snapshot as this system sees it: its record id and its status code."""

    return {
        **ticket,
        "external": link_json(link),
        "crm_status": integration.external_status(TicketStatus(ticket["status"])),
    }


def envelope(
    event: IntegrationEvent, integration: Integration, link: ExternalLink | None
) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "seq": event.seq,
        "type": event.type.value,
        "schema_version": SCHEMA_VERSION,
        "occurred_at": _iso(event.occurred_at),
        "integration_id": str(integration.id),
        "ticket": for_integration(event.payload["ticket"], integration, link),
        "data": event.payload.get("data", {}),
    }
