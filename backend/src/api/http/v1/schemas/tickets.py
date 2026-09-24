"""Response and request bodies of the tickets API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from application.tickets.dto import TicketView
from domain.tickets.enums import ActorRole, ResponsibleParty, TicketStatus
from domain.tickets.state_machine import OPEN, next_statuses


@dataclass(frozen=True, slots=True)
class Viewer:
    """Who is looking: `role` picks the statuses, `user_id` the reporter flags."""

    user_id: int
    role: ActorRole
    demo_mode: bool


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
    escalated_at: datetime | None = Field(
        description="When the reporter asked for a complaint to the housing inspection"
    )
    can_escalate: bool = Field(
        description="The current user (the reporter) may ask for the complaint now"
    )
    can_confirm: bool = Field(
        description="The current user (the reporter) may confirm or reopen now"
    )
    supporters_count: int = Field(
        description='Neighbours who pressed "me too" in the house chat'
    )
    from_house_chat: bool = Field(description="Filed from a house chat card")
    photo_urls: list[str] = Field(description="Photos the resident attached")
    demo_can_expire: bool = Field(
        description="DEMO_MODE: the reporter may move the deadline into the past"
    )

    @classmethod
    def from_view(cls, view: TicketView, viewer: Viewer) -> TicketOut:
        is_reporter = view.reporter_id == viewer.user_id
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
            available_statuses=next_statuses(view.status, viewer.role),
            escalated_at=view.escalated_at,
            can_escalate=is_reporter and view.can_escalate,
            can_confirm=is_reporter and view.status is TicketStatus.DONE,
            supporters_count=view.supporters_count,
            from_house_chat=view.chat_card_mid is not None,
            photo_urls=[photo.url for photo in view.photos],
            demo_can_expire=viewer.demo_mode
            and is_reporter
            and view.status in OPEN
            and not view.is_overdue,
        )


class StatusChangeIn(BaseModel):
    status: Literal["acknowledged", "in_progress", "done", "rejected"]
    comment: str | None = Field(default=None, max_length=500)


class ConfirmationIn(BaseModel):
    resolved: bool = Field(description="true: problem fixed; false: reopen the ticket")
    comment: str | None = Field(default=None, max_length=500)
