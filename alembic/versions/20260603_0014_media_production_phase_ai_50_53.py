"""Media production foundation — media briefs + media assets (AI.50–AI.53).

Revision ID: 20260603_0014
Revises: 20260603_0013
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0014"
down_revision: Union[str, None] = "20260603_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_briefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("content_asset_id", sa.Uuid(), nullable=False),
        sa.Column("source_content_asset_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False, server_default=""),
        sa.Column("target_audience", sa.Text(), nullable=False, server_default=""),
        sa.Column("platform", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("creative_direction", sa.Text(), nullable=False, server_default=""),
        sa.Column("visual_style", sa.Text(), nullable=False, server_default=""),
        sa.Column("composition", sa.Text(), nullable=False, server_default=""),
        sa.Column("text_overlay", sa.Text(), nullable=False, server_default=""),
        sa.Column("references", sa.JSON(), nullable=False),
        sa.Column("submitted_for_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["content_asset_id"], ["content_assets.id"]),
        sa.ForeignKeyConstraint(["source_content_asset_id"], ["content_assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_briefs_owner_id", "media_briefs", ["owner_id"])
    op.create_index("ix_media_briefs_project_id", "media_briefs", ["project_id"])
    op.create_index("ix_media_briefs_content_asset_id", "media_briefs", ["content_asset_id"])
    op.create_index(
        "ix_media_briefs_source_content_asset_id",
        "media_briefs",
        ["source_content_asset_id"],
    )
    op.create_index("ix_media_briefs_status", "media_briefs", ["status"])
    op.create_index(
        "uq_media_briefs_content_asset_id",
        "media_briefs",
        ["content_asset_id"],
        unique=True,
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("media_brief_id", sa.Uuid(), nullable=False),
        sa.Column("source_media_brief_id", sa.Uuid(), nullable=False),
        sa.Column("media_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("generation_provider", sa.String(length=64), nullable=True),
        sa.Column("generation_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["media_brief_id"], ["media_briefs.id"]),
        sa.ForeignKeyConstraint(["source_media_brief_id"], ["media_briefs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_assets_owner_id", "media_assets", ["owner_id"])
    op.create_index("ix_media_assets_project_id", "media_assets", ["project_id"])
    op.create_index("ix_media_assets_media_brief_id", "media_assets", ["media_brief_id"])
    op.create_index(
        "ix_media_assets_source_media_brief_id",
        "media_assets",
        ["source_media_brief_id"],
    )
    op.create_index("ix_media_assets_status", "media_assets", ["status"])
    op.create_index("ix_media_assets_media_type", "media_assets", ["media_type"])
    op.create_index(
        "uq_media_assets_brief_type",
        "media_assets",
        ["media_brief_id", "media_type"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_media_assets_brief_type", "media_assets")
    op.drop_index("ix_media_assets_media_type", "media_assets")
    op.drop_index("ix_media_assets_status", "media_assets")
    op.drop_index("ix_media_assets_source_media_brief_id", "media_assets")
    op.drop_index("ix_media_assets_media_brief_id", "media_assets")
    op.drop_index("ix_media_assets_project_id", "media_assets")
    op.drop_index("ix_media_assets_owner_id", "media_assets")
    op.drop_table("media_assets")
    op.drop_index("uq_media_briefs_content_asset_id", "media_briefs")
    op.drop_index("ix_media_briefs_status", "media_briefs")
    op.drop_index("ix_media_briefs_source_content_asset_id", "media_briefs")
    op.drop_index("ix_media_briefs_content_asset_id", "media_briefs")
    op.drop_index("ix_media_briefs_project_id", "media_briefs")
    op.drop_index("ix_media_briefs_owner_id", "media_briefs")
    op.drop_table("media_briefs")
