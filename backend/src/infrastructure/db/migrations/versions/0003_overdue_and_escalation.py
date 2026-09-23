"""overdue notification and escalation marks on tickets

Tickets already past their deadline are marked as notified, so the first run of
the overdue watcher does not flood dispatchers with old news.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tickets", sa.Column("overdue_notified_at", sa.DateTime(timezone=True))
    )
    op.add_column("tickets", sa.Column("escalated_at", sa.DateTime(timezone=True)))
    op.create_index("ix_tickets_resolve_by", "tickets", ["resolve_by"])
    op.execute(
        "UPDATE tickets SET overdue_notified_at = resolve_by "
        "WHERE resolve_by < now() "
        "AND status NOT IN ('confirmed', 'rejected')"
    )


def downgrade() -> None:
    op.drop_index("ix_tickets_resolve_by", table_name="tickets")
    op.drop_column("tickets", "escalated_at")
    op.drop_column("tickets", "overdue_notified_at")
