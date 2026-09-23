"""Renders the complaint to the housing inspection (PDF in production)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from application.tickets.dto import TicketView


@dataclass(frozen=True, slots=True)
class EscalationDocument:
    """Everything the complaint states; facts only, from the ticket timeline."""

    ticket: TicketView
    company_name: str
    company_phone: str
    region: str
    is_demo: bool
    generated_at: datetime


class EscalationRenderer(Protocol):
    def render(self, document: EscalationDocument) -> bytes: ...


@dataclass(frozen=True, slots=True)
class Leaflet:
    """Notice for the entrance with a QR code to the bot."""

    address: str
    link: str
    company_name: str
    company_phone: str
    is_demo: bool


class LeafletRenderer(Protocol):
    def render(self, leaflet: Leaflet) -> bytes: ...
