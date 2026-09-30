"""integrations with external systems: connections, event feed, ticket links

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("webhook_url", sa.String(2048), nullable=True),
        sa.Column("webhook_secret", sa.String(128), nullable=True),
        sa.Column("event_types", sa.JSON(), nullable=False),
        sa.Column("status_map", sa.JSON(), nullable=False),
        sa.Column("delivered_seq", sa.BigInteger(), nullable=False),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["management_companies.id"],
            name="fk_integrations_company_id_management_companies",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_integrations"),
        sa.UniqueConstraint("key_hash", name="uq_integrations_key_hash"),
    )
    op.create_index("ix_integrations_company_id", "integrations", ["company_id"])

    op.create_table(
        "integration_events",
        sa.Column("seq", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["management_companies.id"],
            name="fk_integration_events_company_id_management_companies",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name="fk_integration_events_ticket_id_tickets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("seq", name="pk_integration_events"),
        sa.UniqueConstraint("id", name="uq_integration_events_id"),
    )
    op.create_index(
        "ix_integration_events_company_seq",
        "integration_events",
        ["company_id", "seq"],
    )

    op.create_table(
        "external_ticket_links",
        sa.Column("integration_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column("external_number", sa.String(200), nullable=True),
        sa.Column("external_url", sa.String(2048), nullable=True),
        sa.Column("external_status", sa.String(100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["integration_id"],
            ["integrations.id"],
            name="fk_external_ticket_links_integration_id_integrations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name="fk_external_ticket_links_ticket_id_tickets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "integration_id", "ticket_id", name="pk_external_ticket_links"
        ),
        sa.UniqueConstraint(
            "integration_id", "external_id", name="uq_external_ticket_links_external"
        ),
    )


def downgrade() -> None:
    op.drop_table("external_ticket_links")
    op.drop_index("ix_integration_events_company_seq", table_name="integration_events")
    op.drop_table("integration_events")
    op.drop_index("ix_integrations_company_id", table_name="integrations")
    op.drop_table("integrations")
