"""ORM rows. They never leave `infrastructure/db` — see `mappers.py`."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Sequence,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


TICKET_NUMBER_SEQ = Sequence("ticket_number_seq", metadata=Base.metadata)


class TicketRow(Base):
    __tablename__ = "tickets"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(32), unique=True)
    reporter_id: Mapped[int] = mapped_column(BigInteger, index=True)
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    category_code: Mapped[str] = mapped_column(String(32))
    is_emergency: Mapped[bool] = mapped_column(Boolean)
    description: Mapped[str] = mapped_column(Text)
    responsible_party: Mapped[str] = mapped_column(String(32))
    responsibility_basis: Mapped[str] = mapped_column(Text)
    resolve_by: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    react_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_basis: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    events: Mapped[list[TicketEventRow]] = relationship(
        back_populates="ticket",
        order_by="TicketEventRow.position",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class TicketEventRow(Base):
    __tablename__ = "ticket_events"
    __table_args__ = (UniqueConstraint("ticket_id", "position"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticket_id: Mapped[UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    actor_role: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    comment: Mapped[str | None] = mapped_column(Text)

    ticket: Mapped[TicketRow] = relationship(back_populates="events")
