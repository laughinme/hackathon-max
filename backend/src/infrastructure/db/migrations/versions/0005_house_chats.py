"""house chats, bot hints, "me too" supports, ticket card in the chat

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("chat_card_mid", sa.String(64)))
    op.create_table(
        "ticket_supports",
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name="fk_ticket_supports_ticket_id_tickets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("ticket_id", "user_id", name="pk_ticket_supports"),
    )
    op.create_table(
        "house_chats",
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("building_id", sa.Uuid(), nullable=True),
        sa.Column("added_by", sa.BigInteger(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["building_id"],
            ["buildings.id"],
            name="fk_house_chats_building_id_buildings",
        ),
        sa.PrimaryKeyConstraint("chat_id", name="pk_house_chats"),
    )
    op.create_index("ix_house_chats_building_id", "house_chats", ["building_id"])
    op.create_table(
        "chat_hints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_mid", sa.String(64), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("category_code", sa.String(32), nullable=False),
        sa.Column("is_emergency", sa.Boolean(), nullable=False),
        sa.Column("needs_emergency_confirmation", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], name="fk_chat_hints_ticket_id_tickets"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chat_hints"),
    )
    op.create_index("ix_chat_hints_chat_id", "chat_hints", ["chat_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_hints_chat_id", table_name="chat_hints")
    op.drop_table("chat_hints")
    op.drop_index("ix_house_chats_building_id", table_name="house_chats")
    op.drop_table("house_chats")
    op.drop_table("ticket_supports")
    op.drop_column("tickets", "chat_card_mid")
