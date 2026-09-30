"""ORM rows of the integration layer. They never leave `infrastructure/db`."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.models import Base


class IntegrationRow(Base):
    """A connected system of a management company and its webhook cursor."""

    __tablename__ = "integrations"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("management_companies.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    key_prefix: Mapped[str] = mapped_column(String(16))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    webhook_url: Mapped[str | None] = mapped_column(String(2048))
    webhook_secret: Mapped[str | None] = mapped_column(String(128))
    event_types: Mapped[list[str]] = mapped_column(JSON)
    status_map: Mapped[dict[str, str]] = mapped_column(JSON)
    delivered_seq: Mapped[int] = mapped_column(BigInteger)
    failures: Mapped[int] = mapped_column(Integer)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class IntegrationEventRow(Base):
    """The company's event feed. `seq` is the cursor for webhooks and polling;
    `recorded_at` is the database's transaction time (see the feed's lag)."""

    __tablename__ = "integration_events"
    __table_args__ = (Index("ix_integration_events_company_seq", "company_id", "seq"),)

    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id: Mapped[UUID] = mapped_column(unique=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("management_companies.id"))
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    payload: Mapped[dict] = mapped_column(JSON)


class ExternalTicketLinkRow(Base):
    """Our ticket <-> the record in a connected system."""

    __tablename__ = "external_ticket_links"
    __table_args__ = (
        UniqueConstraint(
            "integration_id", "external_id", name="uq_external_ticket_links_external"
        ),
    )

    integration_id: Mapped[UUID] = mapped_column(
        ForeignKey("integrations.id", ondelete="CASCADE"), primary_key=True
    )
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True
    )
    external_id: Mapped[str] = mapped_column(String(200))
    external_number: Mapped[str | None] = mapped_column(String(200))
    external_url: Mapped[str | None] = mapped_column(String(2048))
    external_status: Mapped[str | None] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
