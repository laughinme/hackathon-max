"""Base class for business-rule violations raised by the domain layer."""

from __future__ import annotations


class DomainError(Exception):
    """A business rule was violated. Adapters map it to a user-facing message."""

    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
