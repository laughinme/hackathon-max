"""inbox of processed webhook updates

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inbox",
        sa.Column("dedup_key", sa.String(160), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("dedup_key", name="pk_inbox"),
    )
    op.create_index("ix_inbox_received_at", "inbox", ["received_at"])


def downgrade() -> None:
    op.drop_index("ix_inbox_received_at", table_name="inbox")
    op.drop_table("inbox")
