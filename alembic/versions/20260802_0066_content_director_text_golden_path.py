"""Alembic: Content Director Text Golden Path tables (PRODUCT-CD-RUNTIME-01)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0066"
down_revision: Union[str, None] = "20260730_0065"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("context_source", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("objective", sa.String(length=2000), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("audience_description", sa.String(length=2000), nullable=False),
        sa.Column("key_message", sa.String(length=2000), nullable=False),
        sa.Column("offer_value_proposition", sa.String(length=2000), nullable=False),
        sa.Column("tone", sa.String(length=120), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("length", sa.String(length=64), nullable=False),
        sa.Column("cta", sa.String(length=500), nullable=False),
        sa.Column("must_include", sa.String(length=2000), nullable=False),
        sa.Column("must_avoid", sa.String(length=2000), nullable=False),
        sa.Column("requested_variants", sa.Integer(), nullable=False),
        sa.Column("current_run_id", sa.Uuid(), nullable=True),
        sa.Column("approved_asset_id", sa.Uuid(), nullable=True),
        sa.Column("approved_version_number", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "version",
            name="uq_content_requests_project_version",
        ),
    )
    op.create_index("ix_content_requests_owner_id", "content_requests", ["owner_id"])
    op.create_index("ix_content_requests_project_id", "content_requests", ["project_id"])
    op.create_index(
        "ix_content_requests_current_run_id",
        "content_requests",
        ["current_run_id"],
    )
    op.create_index(
        "ix_content_requests_approved_asset_id",
        "content_requests",
        ["approved_asset_id"],
    )

    op.create_table(
        "content_input_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("content_request_id", sa.Uuid(), nullable=False),
        sa.Column("content_request_version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["content_request_id"], ["content_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_content_input_snapshots_request_id",
        "content_input_snapshots",
        ["content_request_id"],
    )
    op.create_index(
        "ix_content_input_snapshots_request_version",
        "content_input_snapshots",
        ["content_request_id", "content_request_version"],
    )

    op.create_table(
        "content_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("content_request_id", sa.Uuid(), nullable=False),
        sa.Column("content_request_version", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["content_request_id"], ["content_requests.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["content_input_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_runs_owner_id", "content_runs", ["owner_id"])
    op.create_index("ix_content_runs_project_id", "content_runs", ["project_id"])
    op.create_index("ix_content_runs_request_id", "content_runs", ["content_request_id"])
    op.create_index("ix_content_runs_status", "content_runs", ["status"])
    op.create_index("ix_content_runs_idempotency_key", "content_runs", ["idempotency_key"])
    op.create_index(
        "ix_content_runs_request_active",
        "content_runs",
        ["content_request_id", "status"],
    )

    op.create_table(
        "content_run_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("content_request_id", sa.Uuid(), nullable=False),
        sa.Column("content_request_version", sa.Integer(), nullable=False),
        sa.Column("content_run_id", sa.Uuid(), nullable=False),
        sa.Column("content_asset_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_index", sa.Integer(), nullable=False),
        sa.Column("rejected", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["content_request_id"], ["content_requests.id"]),
        sa.ForeignKeyConstraint(["content_run_id"], ["content_runs.id"]),
        sa.ForeignKeyConstraint(["content_asset_id"], ["content_assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "content_run_id",
            "candidate_index",
            name="uq_content_run_candidates_run_index",
        ),
    )
    op.create_index(
        "ix_content_run_candidates_run_id",
        "content_run_candidates",
        ["content_run_id"],
    )
    op.create_index(
        "ix_content_run_candidates_asset_id",
        "content_run_candidates",
        ["content_asset_id"],
    )
    op.create_index(
        "ix_content_run_candidates_request_id",
        "content_run_candidates",
        ["content_request_id"],
    )


def downgrade() -> None:
    op.drop_table("content_run_candidates")
    op.drop_table("content_runs")
    op.drop_table("content_input_snapshots")
    op.drop_table("content_requests")
