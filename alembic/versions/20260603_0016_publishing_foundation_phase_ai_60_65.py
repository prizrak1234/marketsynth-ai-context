"""Publishing foundation — package review, jobs, audit (AI.60–AI.65).

Revision ID: 20260603_0016
Revises: 20260603_0015
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0016"
down_revision: Union[str, None] = "20260603_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "publication_packages",
        sa.Column("submitted_for_review_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "publication_packages",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "publication_package_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("publication_package_id", sa.Uuid(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload_snapshot", sa.JSON(), nullable=False),
        sa.Column("result_metadata", sa.JSON(), nullable=False),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(
            ["publication_package_id"],
            ["publication_packages.id"],
        ),
        sa.ForeignKeyConstraint(["channel_id"], ["publishing_channels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_publication_package_jobs_owner_id",
        "publication_package_jobs",
        ["owner_id"],
    )
    op.create_index(
        "ix_publication_package_jobs_project_id",
        "publication_package_jobs",
        ["project_id"],
    )
    op.create_index(
        "ix_publication_package_jobs_publication_package_id",
        "publication_package_jobs",
        ["publication_package_id"],
    )
    op.create_index(
        "ix_publication_package_jobs_channel_id",
        "publication_package_jobs",
        ["channel_id"],
    )
    op.create_index(
        "ix_publication_package_jobs_status",
        "publication_package_jobs",
        ["status"],
    )
    op.create_index(
        "ix_publication_package_jobs_created_at",
        "publication_package_jobs",
        ["created_at"],
    )

    op.create_table(
        "publishing_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=True),
        sa.Column("publication_package_job_id", sa.Uuid(), nullable=True),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["channel_id"], ["publishing_channels.id"]),
        sa.ForeignKeyConstraint(
            ["publication_package_job_id"],
            ["publication_package_jobs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_publishing_audit_events_owner_id",
        "publishing_audit_events",
        ["owner_id"],
    )
    op.create_index(
        "ix_publishing_audit_events_project_id",
        "publishing_audit_events",
        ["project_id"],
    )
    op.create_index(
        "ix_publishing_audit_events_event_type",
        "publishing_audit_events",
        ["event_type"],
    )
    op.create_index(
        "ix_publishing_audit_events_created_at",
        "publishing_audit_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("publishing_audit_events")
    op.drop_table("publication_package_jobs")
    op.drop_column("publication_packages", "approved_at")
    op.drop_column("publication_packages", "submitted_for_review_at")
