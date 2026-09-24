"""photos attached to tickets and chat hints (MAX attachment token and url)

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("photos", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "chat_hints",
        sa.Column("photos", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("chat_hints", "photos")
    op.drop_column("tickets", "photos")
