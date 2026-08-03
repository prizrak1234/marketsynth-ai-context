"""Append-only ImplementationPlan table (Commercial MVP P1.1).

Revision ID: 20260614_0035
Revises: 20260614_0034
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0035"
down_revision: Union[str, None] = "20260614_0034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "implementation_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("marketing_strategy_id", sa.Uuid(), nullable=False),
        sa.Column("marketing_strategy_version", sa.Integer(), nullable=False),
        sa.Column("business_verdict_id", sa.Uuid(), nullable=False),
        sa.Column("business_verdict_version", sa.Integer(), nullable=False),
        sa.Column("evidence_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.Column("plan_origin", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("summary", sa.String(length=4000), nullable=False),
        sa.Column("implementation_horizon", sa.String(length=240), nullable=False),
        sa.Column("workstreams", sa.JSON(), nullable=False),
        sa.Column("milestones", sa.JSON(), nullable=False),
        sa.Column("tasks", sa.JSON(), nullable=False),
        sa.Column("role_assignments", sa.JSON(), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("deliverables", sa.JSON(), nullable=False),
        sa.Column("budget_plan", sa.JSON(), nullable=False),
        sa.Column("budget_gates", sa.JSON(), nullable=False),
        sa.Column("approval_gates", sa.JSON(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("implementation_risks", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("roadmap", sa.JSON(), nullable=False),
        sa.Column("readiness_status", sa.String(length=32), nullable=False),
        sa.Column("readiness_reasons", sa.JSON(), nullable=False),
        sa.Column("submitted_by", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.String(length=2000), nullable=True),
        sa.Column("block_reason", sa.String(length=2000), nullable=True),
        sa.Column("supersedes_plan_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["marketing_strategy_id"], ["marketing_strategies.id"]),
        sa.ForeignKeyConstraint(["business_verdict_id"], ["business_verdicts.id"]),
        sa.ForeignKeyConstraint(
            ["evidence_snapshot_id"], ["business_verdict_evidence_snapshots.id"]
        ),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["supersedes_plan_id"], ["implementation_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "version", name="uq_implementation_plans_project_version"
        ),
    )
    for name, cols in [
        ("ix_implementation_plans_owner_id", ["owner_id"]),
        ("ix_implementation_plans_project_id", ["project_id"]),
        ("ix_implementation_plans_marketing_strategy_id", ["marketing_strategy_id"]),
        ("ix_implementation_plans_lifecycle_status", ["lifecycle_status"]),
        ("ix_implementation_plans_readiness_status", ["readiness_status"]),
        ("ix_implementation_plans_version", ["version"]),
        ("ix_implementation_plans_supersedes_plan_id", ["supersedes_plan_id"]),
        ("ix_implementation_plans_project_id_version", ["project_id", "version"]),
        (
            "ix_implementation_plans_project_id_lifecycle_status",
            ["project_id", "lifecycle_status"],
        ),
        ("ix_implementation_plans_plan_origin", ["plan_origin"]),
        ("ix_implementation_plans_created_at", ["created_at"]),
        ("ix_implementation_plans_approved_at", ["approved_at"]),
    ]:
        op.create_index(name, "implementation_plans", cols)


def downgrade() -> None:
    for name in [
        "ix_implementation_plans_approved_at",
        "ix_implementation_plans_created_at",
        "ix_implementation_plans_plan_origin",
        "ix_implementation_plans_project_id_lifecycle_status",
        "ix_implementation_plans_project_id_version",
        "ix_implementation_plans_supersedes_plan_id",
        "ix_implementation_plans_version",
        "ix_implementation_plans_readiness_status",
        "ix_implementation_plans_lifecycle_status",
        "ix_implementation_plans_marketing_strategy_id",
        "ix_implementation_plans_project_id",
        "ix_implementation_plans_owner_id",
    ]:
        op.drop_index(name, table_name="implementation_plans")
    op.drop_table("implementation_plans")
