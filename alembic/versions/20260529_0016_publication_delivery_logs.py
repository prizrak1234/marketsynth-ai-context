"""Publication delivery logs and job attempts (Phase 6.1).

Revision ID: 20260529_0016
Revises: 20260529_0015
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0016"
down_revision: Union[str, None] = "20260529_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "publication_jobs",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "publication_delivery_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("publication_job_id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("channel_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("response_preview", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["publication_job_id"], ["publication_jobs.id"]),
        sa.ForeignKeyConstraint(["channel_id"], ["publishing_channels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_publication_delivery_logs_owner_id",
        "publication_delivery_logs",
        ["owner_id"],
    )
    op.create_index(
        "ix_publication_delivery_logs_project_id",
        "publication_delivery_logs",
        ["project_id"],
    )
    op.create_index(
        "ix_publication_delivery_logs_publication_job_id",
        "publication_delivery_logs",
        ["publication_job_id"],
    )
    op.create_index(
        "ix_publication_delivery_logs_channel_id",
        "publication_delivery_logs",
        ["channel_id"],
    )
    op.create_index(
        "ix_publication_delivery_logs_channel_type",
        "publication_delivery_logs",
        ["channel_type"],
    )
    op.create_index(
        "ix_publication_delivery_logs_status",
        "publication_delivery_logs",
        ["status"],
    )
    op.create_index(
        "ix_publication_delivery_logs_created_at",
        "publication_delivery_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_publication_delivery_logs_created_at",
        table_name="publication_delivery_logs",
    )
    op.drop_index(
        "ix_publication_delivery_logs_status",
        table_name="publication_delivery_logs",
    )
    op.drop_index(
        "ix_publication_delivery_logs_channel_type",
        table_name="publication_delivery_logs",
    )
    op.drop_index(
        "ix_publication_delivery_logs_channel_id",
        table_name="publication_delivery_logs",
    )
    op.drop_index(
        "ix_publication_delivery_logs_publication_job_id",
        table_name="publication_delivery_logs",
    )
    op.drop_index(
        "ix_publication_delivery_logs_project_id",
        table_name="publication_delivery_logs",
    )
    op.drop_index(
        "ix_publication_delivery_logs_owner_id",
        table_name="publication_delivery_logs",
    )
    op.drop_table("publication_delivery_logs")
    op.drop_column("publication_jobs", "attempts")
