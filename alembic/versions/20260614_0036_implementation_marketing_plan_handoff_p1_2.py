"""Append-only Implementation→MarketingPlan handoff table (Commercial MVP P1.2).

Revision ID: 20260614_0036
Revises: 20260614_0035
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0036"
down_revision: Union[str, None] = "20260614_0035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "implementation_marketing_plan_handoffs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("implementation_plan_id", sa.Uuid(), nullable=False),
        sa.Column("implementation_plan_version", sa.Integer(), nullable=False),
        sa.Column("marketing_strategy_id", sa.Uuid(), nullable=False),
        sa.Column("business_verdict_id", sa.Uuid(), nullable=False),
        sa.Column("source_snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("mapping_version", sa.String(length=64), nullable=False),
        sa.Column("mapping_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.Column("preview_payload", sa.JSON(), nullable=False),
        sa.Column("included_task_count", sa.Integer(), nullable=False),
        sa.Column("excluded_task_count", sa.Integer(), nullable=False),
        sa.Column("blocked_task_count", sa.Integer(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("marketing_plan_id", sa.Uuid(), nullable=True),
        sa.Column("marketing_plan_version", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["implementation_plan_id"], ["implementation_plans.id"]),
        sa.ForeignKeyConstraint(["marketing_strategy_id"], ["marketing_strategies.id"]),
        sa.ForeignKeyConstraint(["business_verdict_id"], ["business_verdicts.id"]),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["marketing_plan_id"], ["marketing_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "mapping_fingerprint",
            name="uq_impl_mp_handoffs_project_fingerprint",
        ),
    )
    for name, cols in [
        ("ix_impl_mp_handoffs_owner_id", ["owner_id"]),
        ("ix_impl_mp_handoffs_project_id", ["project_id"]),
        ("ix_impl_mp_handoffs_implementation_plan_id", ["implementation_plan_id"]),
        ("ix_impl_mp_handoffs_marketing_plan_id", ["marketing_plan_id"]),
        ("ix_impl_mp_handoffs_lifecycle_status", ["lifecycle_status"]),
        ("ix_impl_mp_handoffs_mapping_fingerprint", ["mapping_fingerprint"]),
        (
            "ix_impl_mp_handoffs_plan_id_version",
            ["implementation_plan_id", "implementation_plan_version"],
        ),
        (
            "ix_impl_mp_handoffs_project_fingerprint",
            ["project_id", "mapping_fingerprint"],
        ),
    ]:
        op.create_index(name, "implementation_marketing_plan_handoffs", cols)


def downgrade() -> None:
    for name in [
        "ix_impl_mp_handoffs_project_fingerprint",
        "ix_impl_mp_handoffs_plan_id_version",
        "ix_impl_mp_handoffs_mapping_fingerprint",
        "ix_impl_mp_handoffs_lifecycle_status",
        "ix_impl_mp_handoffs_marketing_plan_id",
        "ix_impl_mp_handoffs_implementation_plan_id",
        "ix_impl_mp_handoffs_project_id",
        "ix_impl_mp_handoffs_owner_id",
    ]:
        op.drop_index(name, table_name="implementation_marketing_plan_handoffs")
    op.drop_table("implementation_marketing_plan_handoffs")
