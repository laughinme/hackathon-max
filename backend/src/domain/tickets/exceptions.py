"""Ticket-specific business-rule violations."""

from __future__ import annotations

from domain.errors import DomainError
from domain.tickets.enums import ActorRole, TicketStatus


class IllegalTransitionError(DomainError):
    code = "illegal_transition"

    def __init__(self, current: TicketStatus, target: TicketStatus) -> None:
        super().__init__(f"Cannot move ticket from {current} to {target}")
        self.current = current
        self.target = target


class ActionNotAllowedError(DomainError):
    code = "action_not_allowed"

    def __init__(self, role: ActorRole, target: TicketStatus) -> None:
        super().__init__(f"Role {role} cannot move ticket to {target}")
        self.role = role
        self.target = target


class NotTicketReporterError(DomainError):
    code = "not_ticket_reporter"

    def __init__(self) -> None:
        super().__init__("Only the reporter can confirm or reopen the ticket")


class TicketNotOverdueError(DomainError):
    code = "ticket_not_overdue"

    def __init__(self) -> None:
        super().__init__(
            "A complaint to the housing inspection is possible only after the "
            "legal deadline has passed and the ticket is still open"
        )


class TicketClosedError(DomainError):
    code = "ticket_closed"

    def __init__(self) -> None:
        super().__init__("The ticket is closed")
