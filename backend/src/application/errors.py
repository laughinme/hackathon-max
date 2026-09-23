"""Errors raised by use cases (as opposed to domain rule violations)."""

from __future__ import annotations

from domain.errors import DomainError


class TicketNotFoundError(DomainError):
    code = "ticket_not_found"

    def __init__(self) -> None:
        super().__init__("Ticket not found")


class DemoActionNotAllowedError(DomainError):
    code = "demo_action_not_allowed"

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
