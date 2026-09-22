"""buildings, companies, residents, dispatchers, outbox, dialog states

Tickets get building_id and company_id (NOT NULL). There are no tickets in any
shared database yet; on a local DB with old tickets run `downgrade base` first.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "management_companies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("region", sa.String(100), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_management_companies"),
    )
    op.create_table(
        "buildings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("address", sa.String(300), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["management_companies.id"],
            name="fk_buildings_company_id_management_companies",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_buildings"),
        sa.UniqueConstraint("code", name="uq_buildings_code"),
    )
    op.create_index("ix_buildings_company_id", "buildings", ["company_id"])
    op.create_table(
        "residents",
        sa.Column("max_user_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("building_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("apartment", sa.String(16), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["building_id"], ["buildings.id"], name="fk_residents_building_id_buildings"
        ),
        sa.PrimaryKeyConstraint("max_user_id", name="pk_residents"),
    )
    op.create_index("ix_residents_building_id", "residents", ["building_id"])
    op.create_table(
        "dispatchers",
        sa.Column("max_user_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["management_companies.id"],
            name="fk_dispatchers_company_id_management_companies",
        ),
        sa.PrimaryKeyConstraint("max_user_id", name="pk_dispatchers"),
    )
    op.create_index("ix_dispatchers_company_id", "dispatchers", ["company_id"])
    op.create_table(
        "outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("recipient_user_id", sa.BigInteger(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_outbox"),
    )
    op.create_index("ix_outbox_next_attempt_at", "outbox", ["next_attempt_at"])
    op.create_table(
        "dialog_states",
        sa.Column("chat_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("state", sa.String(128), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("chat_id", "user_id", name="pk_dialog_states"),
    )
    op.add_column("tickets", sa.Column("building_id", sa.Uuid(), nullable=False))
    op.add_column("tickets", sa.Column("company_id", sa.Uuid(), nullable=False))
    op.create_foreign_key(
        "fk_tickets_building_id_buildings",
        "tickets",
        "buildings",
        ["building_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_tickets_company_id_management_companies",
        "tickets",
        "management_companies",
        ["company_id"],
        ["id"],
    )
    op.create_index("ix_tickets_building_id", "tickets", ["building_id"])
    op.create_index("ix_tickets_company_id", "tickets", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_tickets_company_id", table_name="tickets")
    op.drop_index("ix_tickets_building_id", table_name="tickets")
    op.drop_constraint(
        "fk_tickets_company_id_management_companies", "tickets", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_tickets_building_id_buildings", "tickets", type_="foreignkey"
    )
    op.drop_column("tickets", "company_id")
    op.drop_column("tickets", "building_id")
    op.drop_table("dialog_states")
    op.drop_index("ix_outbox_next_attempt_at", table_name="outbox")
    op.drop_table("outbox")
    op.drop_index("ix_dispatchers_company_id", table_name="dispatchers")
    op.drop_table("dispatchers")
    op.drop_index("ix_residents_building_id", table_name="residents")
    op.drop_table("residents")
    op.drop_index("ix_buildings_company_id", table_name="buildings")
    op.drop_table("buildings")
    op.drop_table("management_companies")
