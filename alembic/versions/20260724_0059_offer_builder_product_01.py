"""Alembic: PRODUCT-01 Offer Builder persistence tables."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260724_0059"
down_revision: Union[str, None] = "20260723_0058"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "offer_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("launch_pack_request_id", sa.Uuid(), nullable=False),
        sa.Column("business_verdict_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("skill_version", sa.String(length=32), nullable=False),
        sa.Column("skill_package_hash", sa.String(length=64), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("approval_status", sa.String(length=32), nullable=False),
        sa.Column("generation_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["launch_pack_request_id"], ["launch_pack_requests.id"]),
        sa.ForeignKeyConstraint(["business_verdict_id"], ["business_verdicts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("launch_pack_request_id", name="uq_offer_launch_pack"),
        sa.UniqueConstraint(
            "owner_id",
            "generation_idempotency_key",
            name="uq_offer_owner_idempotency",
        ),
    )
    op.create_index("ix_offer_owner_project", "offer_artifacts", ["owner_id", "project_id"])
    op.create_index("ix_offer_launch_pack", "offer_artifacts", ["launch_pack_request_id"])
    op.create_index("ix_offer_status", "offer_artifacts", ["approval_status"])
    op.create_index("ix_offer_created_at", "offer_artifacts", ["created_at"])

    op.create_table(
        "offer_artifact_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_artifact_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("offer_title", sa.String(length=512), nullable=False),
        sa.Column("offer_summary", sa.String(length=4000), nullable=False),
        sa.Column("revision_of_id", sa.Uuid(), nullable=True),
        sa.Column("lineage_metadata", sa.JSON(), nullable=False),
        sa.Column("blocker_code", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["offer_artifact_id"], ["offer_artifacts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "offer_artifact_id",
            "version_number",
            name="uq_offer_version_number",
        ),
    )
    op.create_index("ix_offer_version_artifact", "offer_artifact_versions", ["offer_artifact_id"])
    op.create_index("ix_offer_version_status", "offer_artifact_versions", ["status"])
    op.create_index("ix_offer_version_created_at", "offer_artifact_versions", ["created_at"])

    op.create_table(
        "offer_review_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("offer_artifact_id", sa.Uuid(), nullable=False),
        sa.Column("offer_version_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("expected_output_hash", sa.String(length=64), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["offer_artifact_id"], ["offer_artifacts.id"]),
        sa.ForeignKeyConstraint(["offer_version_id"], ["offer_artifact_versions.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "offer_version_id",
            "decision",
            name="uq_offer_review_version_decision",
        ),
    )
    op.create_index("ix_offer_review_artifact", "offer_review_events", ["offer_artifact_id"])
    op.create_index("ix_offer_review_created_at", "offer_review_events", ["created_at"])

    op.create_table(
        "commercial_upstream_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("launch_pack_request_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("source_skill_id", sa.String(length=128), nullable=False),
        sa.Column("source_skill_version", sa.String(length=32), nullable=False),
        sa.Column("source_package_hash", sa.String(length=64), nullable=False),
        sa.Column("source_output_hash", sa.String(length=64), nullable=False),
        sa.Column("source_mode", sa.String(length=32), nullable=False),
        sa.Column("bridge_version", sa.String(length=64), nullable=True),
        sa.Column("source_biv_id", sa.Uuid(), nullable=True),
        sa.Column("source_biv_hash", sa.String(length=64), nullable=True),
        sa.Column("generated_from_fields", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("replacement_required", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["launch_pack_request_id"], ["launch_pack_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "launch_pack_request_id",
            "artifact_type",
            name="uq_upstream_launch_artifact_type",
        ),
    )
    op.create_index(
        "ix_upstream_owner_launch",
        "commercial_upstream_snapshots",
        ["owner_id", "launch_pack_request_id"],
    )
    op.create_index(
        "ix_upstream_type",
        "commercial_upstream_snapshots",
        ["launch_pack_request_id", "artifact_type"],
    )
    op.create_index("ix_upstream_source_mode", "commercial_upstream_snapshots", ["source_mode"])
    op.create_index("ix_upstream_created_at", "commercial_upstream_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_upstream_created_at", table_name="commercial_upstream_snapshots")
    op.drop_index("ix_upstream_source_mode", table_name="commercial_upstream_snapshots")
    op.drop_index("ix_upstream_type", table_name="commercial_upstream_snapshots")
    op.drop_index("ix_upstream_owner_launch", table_name="commercial_upstream_snapshots")
    op.drop_table("commercial_upstream_snapshots")

    op.drop_index("ix_offer_review_created_at", table_name="offer_review_events")
    op.drop_index("ix_offer_review_artifact", table_name="offer_review_events")
    op.drop_table("offer_review_events")

    op.drop_index("ix_offer_version_created_at", table_name="offer_artifact_versions")
    op.drop_index("ix_offer_version_status", table_name="offer_artifact_versions")
    op.drop_index("ix_offer_version_artifact", table_name="offer_artifact_versions")
    op.drop_table("offer_artifact_versions")

    op.drop_index("ix_offer_created_at", table_name="offer_artifacts")
    op.drop_index("ix_offer_status", table_name="offer_artifacts")
    op.drop_index("ix_offer_launch_pack", table_name="offer_artifacts")
    op.drop_index("ix_offer_owner_project", table_name="offer_artifacts")
    op.drop_table("offer_artifacts")
