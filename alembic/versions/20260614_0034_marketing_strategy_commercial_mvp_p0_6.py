"""Append-only MarketingStrategy table (Commercial MVP P0.6).

Revision ID: 20260614_0034
Revises: 20260614_0033
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0034"
down_revision: Union[str, None] = "20260614_0033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_strategies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("business_verdict_id", sa.Uuid(), nullable=False),
        sa.Column("business_verdict_version", sa.Integer(), nullable=False),
        sa.Column("business_verdict_type", sa.String(length=32), nullable=False),
        sa.Column("evidence_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.Column("strategy_origin", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("executive_summary", sa.String(length=4000), nullable=False),
        sa.Column("primary_business_objective", sa.String(length=2000), nullable=False),
        sa.Column("strategic_horizon", sa.String(length=240), nullable=False),
        sa.Column("objectives", sa.JSON(), nullable=False),
        sa.Column("audience_segments", sa.JSON(), nullable=False),
        sa.Column("positioning", sa.JSON(), nullable=False),
        sa.Column("offers", sa.JSON(), nullable=False),
        sa.Column("channel_strategy", sa.JSON(), nullable=False),
        sa.Column("funnel", sa.JSON(), nullable=False),
        sa.Column("asset_plan", sa.JSON(), nullable=False),
        sa.Column("budget_policy", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("verdict_conditions", sa.JSON(), nullable=False),
        sa.Column("strategic_risks", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("execution_constraints", sa.JSON(), nullable=False),
        sa.Column("readiness_status", sa.String(length=32), nullable=False),
        sa.Column("submitted_by", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.String(length=2000), nullable=True),
        sa.Column("supersedes_strategy_id", sa.Uuid(), nullable=True),
        sa.Column("related_marketing_plan_ids", sa.JSON(), nullable=False),
        sa.Column("handoff_status", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["business_verdict_id"], ["business_verdicts.id"]),
        sa.ForeignKeyConstraint(
            ["evidence_snapshot_id"], ["business_verdict_evidence_snapshots.id"]
        ),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["supersedes_strategy_id"], ["marketing_strategies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "version", name="uq_marketing_strategies_project_version"
        ),
    )
    for name, cols in [
        ("ix_marketing_strategies_owner_id", ["owner_id"]),
        ("ix_marketing_strategies_project_id", ["project_id"]),
        ("ix_marketing_strategies_business_verdict_id", ["business_verdict_id"]),
        ("ix_marketing_strategies_lifecycle_status", ["lifecycle_status"]),
        ("ix_marketing_strategies_readiness_status", ["readiness_status"]),
        ("ix_marketing_strategies_version", ["version"]),
        ("ix_marketing_strategies_supersedes_strategy_id", ["supersedes_strategy_id"]),
        ("ix_marketing_strategies_project_id_version", ["project_id", "version"]),
        (
            "ix_marketing_strategies_project_id_lifecycle_status",
            ["project_id", "lifecycle_status"],
        ),
        ("ix_marketing_strategies_strategy_origin", ["strategy_origin"]),
        ("ix_marketing_strategies_created_at", ["created_at"]),
        ("ix_marketing_strategies_approved_at", ["approved_at"]),
    ]:
        op.create_index(name, "marketing_strategies", cols)


def downgrade() -> None:
    for name in [
        "ix_marketing_strategies_approved_at",
        "ix_marketing_strategies_created_at",
        "ix_marketing_strategies_strategy_origin",
        "ix_marketing_strategies_project_id_lifecycle_status",
        "ix_marketing_strategies_project_id_version",
        "ix_marketing_strategies_supersedes_strategy_id",
        "ix_marketing_strategies_version",
        "ix_marketing_strategies_readiness_status",
        "ix_marketing_strategies_lifecycle_status",
        "ix_marketing_strategies_business_verdict_id",
        "ix_marketing_strategies_project_id",
        "ix_marketing_strategies_owner_id",
    ]:
        op.drop_index(name, table_name="marketing_strategies")
    op.drop_table("marketing_strategies")
