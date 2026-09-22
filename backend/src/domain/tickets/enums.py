"""Enumerations of the ticket aggregate."""

from __future__ import annotations

from enum import StrEnum


class TicketStatus(StrEnum):
    """Lifecycle of a ticket. Allowed moves live in `state_machine.py`."""

    REGISTERED = "registered"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class ActorRole(StrEnum):
    """Who performs an action on a ticket."""

    RESIDENT = "resident"
    DISPATCHER = "dispatcher"
    SYSTEM = "system"


class ResponsibleParty(StrEnum):
    """Organisation that is legally responsible for fixing the problem."""

    MANAGEMENT_COMPANY = "management_company"
    RESOURCE_SUPPLIER = "resource_supplier"
    CAPITAL_REPAIR_OPERATOR = "capital_repair_operator"
    MUNICIPALITY = "municipality"
    OWNER = "owner"
