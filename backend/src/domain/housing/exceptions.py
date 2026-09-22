from __future__ import annotations

from domain.errors import DomainError


class BuildingNotFoundError(DomainError):
    code = "building_not_found"

    def __init__(self) -> None:
        super().__init__("Building not found")


class ResidentNotBoundError(DomainError):
    code = "resident_not_bound"

    def __init__(self) -> None:
        super().__init__("Choose your building first")


class NotADispatcherError(DomainError):
    code = "not_a_dispatcher"

    def __init__(self) -> None:
        super().__init__("Only a dispatcher of the management company can do this")
