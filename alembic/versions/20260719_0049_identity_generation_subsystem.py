"""H2.8E — identity reference manifests + qualification runs.

Revision ID: 20260719_0049
Revises: 20260718_0048
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260719_0049"
down_revision: Union[str, None] = "20260718_0048"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "identity_reference_manifests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("reference_set_id", sa.Uuid(), nullable=False),
        sa.Column("reference_set_version", sa.String(length=128), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("primary_reference_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("immutable_hash", sa.String(length=128), nullable=False),
        sa.Column("selection_policy_version", sa.String(length=32), nullable=False),
        sa.Column("provider_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reference_set_id"], ["reference_sets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_identity_reference_manifests_owner_id",
        "identity_reference_manifests",
        ["owner_id"],
    )
    op.create_index(
        "ix_identity_reference_manifests_reference_set_id",
        "identity_reference_manifests",
        ["reference_set_id"],
    )
    op.create_index(
        "ix_identity_reference_manifests_immutable_hash",
        "identity_reference_manifests",
        ["immutable_hash"],
    )

    op.create_table(
        "identity_qualification_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("baseline_asset_id", sa.Uuid(), nullable=True),
        sa.Column("reference_set_id", sa.Uuid(), nullable=False),
        sa.Column("manifest_id", sa.Uuid(), nullable=True),
        sa.Column("manifest_hash", sa.String(length=128), nullable=True),
        sa.Column("provider_code", sa.String(length=64), nullable=False),
        sa.Column("prompt_summary", sa.String(length=500), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("variants", sa.JSON(), nullable=False),
        sa.Column("paid_approval", sa.JSON(), nullable=True),
        sa.Column("readiness_snapshot", sa.JSON(), nullable=True),
        sa.Column("capability_status", sa.String(length=64), nullable=False),
        sa.Column("owner_review_result", sa.String(length=128), nullable=True),
        sa.Column("consistency_assist", sa.String(length=64), nullable=True),
        sa.Column("report_summary", sa.String(length=2000), nullable=True),
        sa.Column("operator_state", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["baseline_asset_id"], ["generated_visual_assets.id"]),
        sa.ForeignKeyConstraint(["reference_set_id"], ["reference_sets.id"]),
        sa.ForeignKeyConstraint(["manifest_id"], ["identity_reference_manifests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_identity_qualification_runs_owner_id",
        "identity_qualification_runs",
        ["owner_id"],
    )
    op.create_index(
        "ix_identity_qualification_runs_status",
        "identity_qualification_runs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_qualification_runs_status",
        table_name="identity_qualification_runs",
    )
    op.drop_index(
        "ix_identity_qualification_runs_owner_id",
        table_name="identity_qualification_runs",
    )
    op.drop_table("identity_qualification_runs")
    op.drop_index(
        "ix_identity_reference_manifests_immutable_hash",
        table_name="identity_reference_manifests",
    )
    op.drop_index(
        "ix_identity_reference_manifests_reference_set_id",
        table_name="identity_reference_manifests",
    )
    op.drop_index(
        "ix_identity_reference_manifests_owner_id",
        table_name="identity_reference_manifests",
    )
    op.drop_table("identity_reference_manifests")
