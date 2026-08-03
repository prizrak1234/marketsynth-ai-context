"""Content production layer — asset review audit + publication packages (AI.42–AI.43).

Revision ID: 20260603_0013
Revises: 20260603_0012
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0013"
down_revision: Union[str, None] = "20260603_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "content_assets",
        sa.Column("submitted_for_review_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "content_assets",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "publication_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("content_asset_id", sa.Uuid(), nullable=False),
        sa.Column("source_content_asset_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("cta", sa.String(length=512), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["content_asset_id"], ["content_assets.id"]),
        sa.ForeignKeyConstraint(["source_content_asset_id"], ["content_assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_publication_packages_owner_id",
        "publication_packages",
        ["owner_id"],
    )
    op.create_index(
        "ix_publication_packages_project_id",
        "publication_packages",
        ["project_id"],
    )
    op.create_index(
        "ix_publication_packages_content_asset_id",
        "publication_packages",
        ["content_asset_id"],
    )
    op.create_index(
        "ix_publication_packages_source_content_asset_id",
        "publication_packages",
        ["source_content_asset_id"],
    )
    op.create_index(
        "ix_publication_packages_status",
        "publication_packages",
        ["status"],
    )
    op.create_index(
        "uq_publication_packages_asset_channel",
        "publication_packages",
        ["content_asset_id", "channel"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_publication_packages_asset_channel", "publication_packages")
    op.drop_index("ix_publication_packages_status", "publication_packages")
    op.drop_index("ix_publication_packages_source_content_asset_id", "publication_packages")
    op.drop_index("ix_publication_packages_content_asset_id", "publication_packages")
    op.drop_index("ix_publication_packages_project_id", "publication_packages")
    op.drop_index("ix_publication_packages_owner_id", "publication_packages")
    op.drop_table("publication_packages")
    op.drop_column("content_assets", "approved_at")
    op.drop_column("content_assets", "submitted_for_review_at")
