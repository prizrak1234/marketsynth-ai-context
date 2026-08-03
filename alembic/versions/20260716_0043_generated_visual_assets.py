"""Alembic: generated_visual_assets + UserRequest generation fields (H2.6A).

Revision ID: 20260716_0043
Revises: 20260716_0042
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0043"
down_revision: Union[str, None] = "20260716_0042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "generated_visual_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("user_request_id", sa.Uuid(), nullable=False),
        sa.Column("skill_code", sa.String(length=128), nullable=False),
        sa.Column("skill_version", sa.String(length=32), nullable=False),
        sa.Column("knowledge_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_summary", sa.String(length=1000), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("storage_uri", sa.String(length=1000), nullable=True),
        sa.Column("content_path", sa.String(length=1000), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("safety_result", sa.String(length=64), nullable=False),
        sa.Column("generation_metadata", sa.JSON(), nullable=False),
        sa.Column("error_category", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.ForeignKeyConstraint(["knowledge_snapshot_id"], ["knowledge_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generated_visual_assets_owner_id",
        "generated_visual_assets",
        ["owner_id"],
    )
    op.create_index(
        "ix_generated_visual_assets_user_request_id",
        "generated_visual_assets",
        ["user_request_id"],
    )
    op.create_index(
        "ix_generated_visual_assets_status",
        "generated_visual_assets",
        ["status"],
    )

    op.add_column(
        "user_requests",
        sa.Column("generated_visual_asset_ids", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "user_requests",
        sa.Column("generation_status", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "user_requests",
        sa.Column("generation_warnings", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("user_requests", "generation_warnings")
    op.drop_column("user_requests", "generation_status")
    op.drop_column("user_requests", "generated_visual_asset_ids")
    op.drop_index("ix_generated_visual_assets_status", table_name="generated_visual_assets")
    op.drop_index(
        "ix_generated_visual_assets_user_request_id",
        table_name="generated_visual_assets",
    )
    op.drop_index("ix_generated_visual_assets_owner_id", table_name="generated_visual_assets")
    op.drop_table("generated_visual_assets")
