"""Publication job scheduling (Phase 8.0).

Revision ID: 20260602_0001
Revises: 20260529_0016
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_0001"
down_revision: Union[str, None] = "20260529_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "publication_jobs",
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "publication_jobs",
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_publication_jobs_scheduled_at",
        "publication_jobs",
        ["scheduled_at"],
    )
    op.create_index(
        "ix_publication_jobs_queued_at",
        "publication_jobs",
        ["queued_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_publication_jobs_queued_at", table_name="publication_jobs")
    op.drop_index("ix_publication_jobs_scheduled_at", table_name="publication_jobs")
    op.drop_column("publication_jobs", "queued_at")
    op.drop_column("publication_jobs", "scheduled_at")

