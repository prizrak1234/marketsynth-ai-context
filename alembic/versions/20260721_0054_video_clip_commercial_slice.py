"""Alembic: VS.2A video clip commercial slice."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0054"
down_revision: Union[str, None] = "20260719_0050"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "video_clip_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("user_request_id", sa.Uuid(), nullable=True),
        sa.Column("source_image_asset_id", sa.Uuid(), nullable=False),
        sa.Column("motion_brief", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("preview_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("estimated_cost_units", sa.String(length=32), nullable=True),
        sa.Column("quote_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approved_request_hash", sa.String(length=128), nullable=True),
        sa.Column("provider_job_id", sa.String(length=256), nullable=True),
        sa.Column("provider_code", sa.String(length=64), nullable=True),
        sa.Column("execution_evidence_json", sa.JSON(), nullable=False),
        sa.Column("scene_graph_json", sa.JSON(), nullable=False),
        sa.Column("result_asset_id", sa.Uuid(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message_ru", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.ForeignKeyConstraint(["source_image_asset_id"], ["generated_visual_assets.id"]),
        sa.ForeignKeyConstraint(["result_asset_id"], ["generated_visual_assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "idempotency_key", name="uq_video_clip_owner_idempotency"),
    )
    op.create_index("ix_video_clip_requests_owner", "video_clip_requests", ["owner_id"])
    op.create_index("ix_video_clip_requests_status", "video_clip_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_video_clip_requests_status", table_name="video_clip_requests")
    op.drop_index("ix_video_clip_requests_owner", table_name="video_clip_requests")
    op.drop_table("video_clip_requests")
