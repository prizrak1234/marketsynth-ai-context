"""Publishing scheduler fields on package jobs (AI.76–AI.78).

Revision ID: 20260603_0018
Revises: 20260603_0017
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0018"
down_revision: Union[str, None] = "20260603_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "publication_package_jobs",
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "publication_package_jobs",
        sa.Column(
            "schedule_status",
            sa.String(length=32),
            nullable=False,
            server_default="unscheduled",
        ),
    )
    op.add_column(
        "publication_package_jobs",
        sa.Column("dispatch_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "publication_package_jobs",
        sa.Column("last_dispatch_error", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_publication_package_jobs_schedule_status",
        "publication_package_jobs",
        ["schedule_status"],
    )
    op.create_index(
        "ix_publication_package_jobs_scheduled_for",
        "publication_package_jobs",
        ["scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_publication_package_jobs_scheduled_for",
        table_name="publication_package_jobs",
    )
    op.drop_index(
        "ix_publication_package_jobs_schedule_status",
        table_name="publication_package_jobs",
    )
    op.drop_column("publication_package_jobs", "last_dispatch_error")
    op.drop_column("publication_package_jobs", "dispatch_attempts")
    op.drop_column("publication_package_jobs", "schedule_status")
    op.drop_column("publication_package_jobs", "scheduled_for")
