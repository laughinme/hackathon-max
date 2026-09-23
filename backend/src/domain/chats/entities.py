"""House chats the bot was added to, and the bot's hints on complaints there."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class HouseChat:
    """A MAX group chat of one building. We keep our own registry: the MAX API
    has no "list my chats" (GET /chats was removed)."""

    chat_id: int
    added_by: int
    added_at: datetime
    building_id: UUID | None = None
    is_active: bool = True

    @property
    def is_bound(self) -> bool:
        return self.is_active and self.building_id is not None

    def bind(self, building_id: UUID) -> None:
        self.building_id = building_id
        self.is_active = True

    def rejoin(self, user_id: int, now: datetime) -> None:
        """The bot was added again: keep the building, it is still that house."""

        self.is_active = True
        self.added_by = user_id
        self.added_at = now

    def leave(self) -> None:
        self.is_active = False


@dataclass(slots=True)
class ChatHint:
    """The bot noticed a complaint in a house chat and offered to file it.

    The text lives here, never in button payloads. `ticket_id` is set once:
    two neighbours pressing "file" at the same time get the same ticket.
    """

    chat_id: int
    message_mid: str
    author_id: int
    text: str
    category_code: str
    is_emergency: bool
    needs_emergency_confirmation: bool
    created_at: datetime
    id: UUID = field(default_factory=uuid4)
    ticket_id: UUID | None = None

    @property
    def is_filed(self) -> bool:
        return self.ticket_id is not None

    def mark_filed(self, ticket_id: UUID) -> None:
        if self.ticket_id is None:
            self.ticket_id = ticket_id
