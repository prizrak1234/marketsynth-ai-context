"""Media generation jobs + asset storage boundary (AI.56–AI.58).

Revision ID: 20260603_0015
Revises: 20260603_0014
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0015"
down_revision: Union[str, None] = "20260603_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_generation_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("media_brief_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("media_type", sa.String(length=32), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result_metadata", sa.JSON(), nullable=False),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["media_brief_id"], ["media_briefs.id"]),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_generation_jobs_owner_id", "media_generation_jobs", ["owner_id"])
    op.create_index(
        "ix_media_generation_jobs_project_id",
        "media_generation_jobs",
        ["project_id"],
    )
    op.create_index(
        "ix_media_generation_jobs_media_brief_id",
        "media_generation_jobs",
        ["media_brief_id"],
    )
    op.create_index(
        "ix_media_generation_jobs_media_asset_id",
        "media_generation_jobs",
        ["media_asset_id"],
    )
    op.create_index("ix_media_generation_jobs_status", "media_generation_jobs", ["status"])

    op.add_column(
        "media_assets",
        sa.Column("source_generation_job_id", sa.Uuid(), nullable=True),
    )
    op.add_column("media_assets", sa.Column("provider", sa.String(length=64), nullable=True))
    op.add_column(
        "media_assets",
        sa.Column("provider_asset_ref", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("storage_uri", sa.String(length=512), nullable=True),
    )
    op.add_column("media_assets", sa.Column("mime_type", sa.String(length=64), nullable=True))
    op.add_column("media_assets", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("media_assets", sa.Column("height", sa.Integer(), nullable=True))
    op.add_column(
        "media_assets",
        sa.Column("current_version_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_foreign_key(
        "fk_media_assets_source_generation_job_id",
        "media_assets",
        "media_generation_jobs",
        ["source_generation_job_id"],
        ["id"],
    )
    op.create_index(
        "ix_media_assets_source_generation_job_id",
        "media_assets",
        ["source_generation_job_id"],
    )

    op.create_table(
        "media_asset_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_generation_job_id", sa.Uuid(), nullable=True),
        sa.Column("storage_uri", sa.String(length=512), nullable=True),
        sa.Column("provider_asset_ref", sa.String(length=512), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["media_asset_id"], ["media_assets.id"]),
        sa.ForeignKeyConstraint(["source_generation_job_id"], ["media_generation_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_media_asset_versions_media_asset_id",
        "media_asset_versions",
        ["media_asset_id"],
    )
    op.create_index(
        "uq_media_asset_versions_asset_version",
        "media_asset_versions",
        ["media_asset_id", "version_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_media_asset_versions_asset_version", "media_asset_versions")
    op.drop_index("ix_media_asset_versions_media_asset_id", "media_asset_versions")
    op.drop_table("media_asset_versions")
    op.drop_index("ix_media_assets_source_generation_job_id", "media_assets")
    op.drop_constraint("fk_media_assets_source_generation_job_id", "media_assets", type_="foreignkey")
    op.drop_column("media_assets", "current_version_number")
    op.drop_column("media_assets", "height")
    op.drop_column("media_assets", "width")
    op.drop_column("media_assets", "mime_type")
    op.drop_column("media_assets", "storage_uri")
    op.drop_column("media_assets", "provider_asset_ref")
    op.drop_column("media_assets", "provider")
    op.drop_column("media_assets", "source_generation_job_id")
    op.drop_index("ix_media_generation_jobs_status", "media_generation_jobs")
    op.drop_index("ix_media_generation_jobs_media_asset_id", "media_generation_jobs")
    op.drop_index("ix_media_generation_jobs_media_brief_id", "media_generation_jobs")
    op.drop_index("ix_media_generation_jobs_project_id", "media_generation_jobs")
    op.drop_index("ix_media_generation_jobs_owner_id", "media_generation_jobs")
    op.drop_table("media_generation_jobs")
