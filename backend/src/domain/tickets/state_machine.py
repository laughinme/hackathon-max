"""Allowed status transitions and the roles that may perform them.

The table is the single source of truth: the aggregate, the bot and the
dispatcher UI all ask it instead of hard-coding their own rules.
"""

from __future__ import annotations

from domain.tickets.enums import ActorRole, TicketStatus
from domain.tickets.exceptions import ActionNotAllowedError, IllegalTransitionError

S = TicketStatus
DISPATCHER = frozenset({ActorRole.DISPATCHER})
RESIDENT = frozenset({ActorRole.RESIDENT})

TRANSITIONS: dict[tuple[TicketStatus, TicketStatus], frozenset[ActorRole]] = {
    (S.REGISTERED, S.ACKNOWLEDGED): DISPATCHER,
    (S.REGISTERED, S.IN_PROGRESS): DISPATCHER,
    (S.ACKNOWLEDGED, S.IN_PROGRESS): DISPATCHER,
    (S.REGISTERED, S.DONE): DISPATCHER,
    (S.ACKNOWLEDGED, S.DONE): DISPATCHER,
    (S.IN_PROGRESS, S.DONE): DISPATCHER,
    (S.REGISTERED, S.REJECTED): DISPATCHER,
    (S.ACKNOWLEDGED, S.REJECTED): DISPATCHER,
    (S.IN_PROGRESS, S.REJECTED): DISPATCHER,
    # The resident closes the loop: confirms the fix or reopens the ticket.
    (S.DONE, S.CONFIRMED): RESIDENT,
    (S.DONE, S.IN_PROGRESS): RESIDENT,
}

TERMINAL: frozenset[TicketStatus] = frozenset({S.CONFIRMED, S.REJECTED})
OPEN: frozenset[TicketStatus] = frozenset({S.REGISTERED, S.ACKNOWLEDGED, S.IN_PROGRESS})


def ensure_transition(
    current: TicketStatus, target: TicketStatus, role: ActorRole
) -> None:
    """Raise if `role` may not move a ticket from `current` to `target`."""

    allowed_roles = TRANSITIONS.get((current, target))
    if allowed_roles is None:
        raise IllegalTransitionError(current, target)
    if role not in allowed_roles:
        raise ActionNotAllowedError(role, target)


def next_statuses(current: TicketStatus, role: ActorRole) -> list[TicketStatus]:
    """Statuses `role` can move the ticket to from `current` (for UI buttons)."""

    return [
        target
        for (source, target), roles in TRANSITIONS.items()
        if source == current and role in roles
    ]
