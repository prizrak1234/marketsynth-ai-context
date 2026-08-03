"""Publishing channels and publication jobs (Phase 6.0).

Revision ID: 20260529_0015
Revises: 20260529_0014
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0015"
down_revision: Union[str, None] = "20260529_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "publishing_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("channel_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("channel_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("config_preview", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_publishing_channels_owner_id",
        "publishing_channels",
        ["owner_id"],
    )
    op.create_index(
        "ix_publishing_channels_project_id",
        "publishing_channels",
        ["project_id"],
    )
    op.create_index(
        "ix_publishing_channels_type",
        "publishing_channels",
        ["channel_type"],
    )
    op.create_index(
        "ix_publishing_channels_status",
        "publishing_channels",
        ["status"],
    )

    op.create_table(
        "publication_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("asset_version_number", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("payload_preview", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["content_assets.id"]),
        sa.ForeignKeyConstraint(["channel_id"], ["publishing_channels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_publication_jobs_owner_id", "publication_jobs", ["owner_id"])
    op.create_index(
        "ix_publication_jobs_project_id",
        "publication_jobs",
        ["project_id"],
    )
    op.create_index("ix_publication_jobs_asset_id", "publication_jobs", ["asset_id"])
    op.create_index(
        "ix_publication_jobs_channel_id",
        "publication_jobs",
        ["channel_id"],
    )
    op.create_index("ix_publication_jobs_status", "publication_jobs", ["status"])
    op.create_index(
        "ix_publication_jobs_created_at",
        "publication_jobs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_publication_jobs_created_at", table_name="publication_jobs")
    op.drop_index("ix_publication_jobs_status", table_name="publication_jobs")
    op.drop_index("ix_publication_jobs_channel_id", table_name="publication_jobs")
    op.drop_index("ix_publication_jobs_asset_id", table_name="publication_jobs")
    op.drop_index("ix_publication_jobs_project_id", table_name="publication_jobs")
    op.drop_index("ix_publication_jobs_owner_id", table_name="publication_jobs")
    op.drop_table("publication_jobs")

    op.drop_index("ix_publishing_channels_status", table_name="publishing_channels")
    op.drop_index("ix_publishing_channels_type", table_name="publishing_channels")
    op.drop_index("ix_publishing_channels_project_id", table_name="publishing_channels")
    op.drop_index("ix_publishing_channels_owner_id", table_name="publishing_channels")
    op.drop_table("publishing_channels")
