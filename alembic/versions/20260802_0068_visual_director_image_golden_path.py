"""Alembic: Visual Director Image Golden Path tables (PRODUCT-CD-RUNTIME-02)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0068"
down_revision: Union[str, None] = "20260802_0067"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "visual_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("context_source", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("objective", sa.String(length=2000), nullable=False),
        sa.Column("scene_description", sa.String(length=4000), nullable=False),
        sa.Column("subject", sa.String(length=1000), nullable=False),
        sa.Column("style", sa.String(length=240), nullable=False),
        sa.Column("audience", sa.String(length=2000), nullable=False),
        sa.Column("mood", sa.String(length=240), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False),
        sa.Column("visual_format", sa.String(length=64), nullable=False),
        sa.Column("requested_variants", sa.Integer(), nullable=False),
        sa.Column("text_overlay", sa.String(length=500), nullable=False),
        sa.Column("must_include", sa.String(length=2000), nullable=False),
        sa.Column("must_avoid", sa.String(length=2000), nullable=False),
        sa.Column("related_text_asset_id", sa.Uuid(), nullable=True),
        sa.Column("reference_asset_ids", sa.JSON(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("current_run_id", sa.Uuid(), nullable=True),
        sa.Column("approved_asset_id", sa.Uuid(), nullable=True),
        sa.Column("approved_version_number", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "version",
            name="uq_visual_requests_project_version",
        ),
    )
    op.create_index("ix_visual_requests_owner_id", "visual_requests", ["owner_id"])
    op.create_index("ix_visual_requests_project_id", "visual_requests", ["project_id"])
    op.create_index(
        "ix_visual_requests_current_run_id",
        "visual_requests",
        ["current_run_id"],
    )
    op.create_index(
        "ix_visual_requests_approved_asset_id",
        "visual_requests",
        ["approved_asset_id"],
    )

    op.create_table(
        "visual_input_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("visual_request_id", sa.Uuid(), nullable=False),
        sa.Column("visual_request_version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["visual_request_id"], ["visual_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_visual_input_snapshots_request_id",
        "visual_input_snapshots",
        ["visual_request_id"],
    )
    op.create_index(
        "ix_visual_input_snapshots_request_version",
        "visual_input_snapshots",
        ["visual_request_id", "visual_request_version"],
    )

    op.create_table(
        "visual_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("visual_request_id", sa.Uuid(), nullable=False),
        sa.Column("visual_request_version", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["visual_request_id"], ["visual_requests.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["visual_input_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_visual_runs_owner_id", "visual_runs", ["owner_id"])
    op.create_index("ix_visual_runs_project_id", "visual_runs", ["project_id"])
    op.create_index("ix_visual_runs_request_id", "visual_runs", ["visual_request_id"])
    op.create_index("ix_visual_runs_status", "visual_runs", ["status"])
    op.create_index("ix_visual_runs_idempotency_key", "visual_runs", ["idempotency_key"])
    op.create_index(
        "ix_visual_runs_request_active",
        "visual_runs",
        ["visual_request_id", "status"],
    )

    op.create_table(
        "image_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_version_number", sa.Integer(), nullable=False),
        sa.Column("approved_version_number", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("content_path", sa.String(length=1000), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("asset_metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_assets_owner_id", "image_assets", ["owner_id"])
    op.create_index("ix_image_assets_project_id", "image_assets", ["project_id"])
    op.create_index("ix_image_assets_status", "image_assets", ["status"])

    op.create_table(
        "image_asset_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("image_asset_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("content_path", sa.String(length=1000), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("asset_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["image_asset_id"], ["image_assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "image_asset_id",
            "version_number",
            name="uq_image_asset_versions_asset_version",
        ),
    )
    op.create_index(
        "ix_image_asset_versions_asset_id",
        "image_asset_versions",
        ["image_asset_id"],
    )

    op.create_table(
        "visual_run_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("visual_request_id", sa.Uuid(), nullable=False),
        sa.Column("visual_request_version", sa.Integer(), nullable=False),
        sa.Column("visual_run_id", sa.Uuid(), nullable=False),
        sa.Column("image_asset_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_index", sa.Integer(), nullable=False),
        sa.Column("rejected", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["visual_request_id"], ["visual_requests.id"]),
        sa.ForeignKeyConstraint(["visual_run_id"], ["visual_runs.id"]),
        sa.ForeignKeyConstraint(["image_asset_id"], ["image_assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "visual_run_id",
            "candidate_index",
            name="uq_visual_run_candidates_run_index",
        ),
    )
    op.create_index(
        "ix_visual_run_candidates_run_id",
        "visual_run_candidates",
        ["visual_run_id"],
    )
    op.create_index(
        "ix_visual_run_candidates_asset_id",
        "visual_run_candidates",
        ["image_asset_id"],
    )
    op.create_index(
        "ix_visual_run_candidates_request_id",
        "visual_run_candidates",
        ["visual_request_id"],
    )


def downgrade() -> None:
    op.drop_table("visual_run_candidates")
    op.drop_table("image_asset_versions")
    op.drop_table("image_assets")
    op.drop_table("visual_runs")
    op.drop_table("visual_input_snapshots")
    op.drop_table("visual_requests")
