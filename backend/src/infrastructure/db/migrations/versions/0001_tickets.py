"""tickets and ticket events

Revision ID: 0001
Revises:
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSequence(sa.Sequence("ticket_number_seq")))
    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(32), nullable=False),
        sa.Column("reporter_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=True),
        sa.Column("category_code", sa.String(32), nullable=False),
        sa.Column("is_emergency", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("responsible_party", sa.String(32), nullable=False),
        sa.Column("responsibility_basis", sa.Text(), nullable=False),
        sa.Column("resolve_by", sa.DateTime(timezone=True), nullable=False),
        sa.Column("react_by", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_basis", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_tickets"),
        sa.UniqueConstraint("number", name="uq_tickets_number"),
    )
    op.create_index("ix_tickets_reporter_id", "tickets", ["reporter_id"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_table(
        "ticket_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("actor_role", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name="fk_ticket_events_ticket_id_tickets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ticket_events"),
        sa.UniqueConstraint("ticket_id", "position", name="uq_ticket_events_ticket_id"),
    )


def downgrade() -> None:
    op.drop_table("ticket_events")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_reporter_id", table_name="tickets")
    op.drop_table("tickets")
    op.execute(sa.schema.DropSequence(sa.Sequence("ticket_number_seq")))
