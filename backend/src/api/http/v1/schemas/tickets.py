"""Response and request bodies of the tickets API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from application.tickets.dto import TicketView
from domain.tickets.enums import ActorRole, ResponsibleParty, TicketStatus
from domain.tickets.state_machine import next_statuses


class TicketEventOut(BaseModel):
    status: TicketStatus
    actor_role: ActorRole
    at: datetime
    comment: str | None


class TicketOut(BaseModel):
    id: UUID
    number: str
    building_id: UUID
    building_address: str
    category_code: str
    is_emergency: bool
    description: str
    responsible_party: ResponsibleParty
    responsibility_basis: str
    status: TicketStatus
    resolve_by: datetime
    react_by: datetime | None
    deadline_basis: str
    is_overdue: bool
    created_at: datetime
    updated_at: datetime
    events: list[TicketEventOut]
    available_statuses: list[TicketStatus] = Field(
        description="Statuses the current user may move this ticket to"
    )

    @classmethod
    def from_view(cls, view: TicketView, role: ActorRole) -> TicketOut:
        return cls(
            id=view.id,
            number=view.number,
            building_id=view.building_id,
            building_address=view.building_address,
            category_code=view.category_code,
            is_emergency=view.is_emergency,
            description=view.description,
            responsible_party=view.responsible_party,
            responsibility_basis=view.responsibility_basis,
            status=view.status,
            resolve_by=view.resolve_by,
            react_by=view.react_by,
            deadline_basis=view.deadline_basis,
            is_overdue=view.is_overdue,
            created_at=view.created_at,
            updated_at=view.updated_at,
            events=[
                TicketEventOut(
                    status=event.status,
                    actor_role=event.actor_role,
                    at=event.at,
                    comment=event.comment,
                )
                for event in view.events
            ],
            available_statuses=next_statuses(view.status, role),
        )


class StatusChangeIn(BaseModel):
    status: Literal["acknowledged", "in_progress", "done", "rejected"]
    comment: str | None = Field(default=None, max_length=500)


class ConfirmationIn(BaseModel):
    resolved: bool = Field(description="true: problem fixed; false: reopen the ticket")
    comment: str | None = Field(default=None, max_length=500)
