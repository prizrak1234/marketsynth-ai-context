"""Marketing plan execution runs (Phase AI.29).

Revision ID: 20260603_0010
Revises: 20260603_0009
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0010"
down_revision: Union[str, None] = "20260603_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_plan_execution_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("marketing_plan_id", sa.Uuid(), nullable=False),
        sa.Column("marketing_plan_version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("task_snapshots", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["marketing_plan_id"], ["marketing_plans.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_marketing_plan_execution_runs_owner_id",
        "marketing_plan_execution_runs",
        ["owner_id"],
    )
    op.create_index(
        "ix_marketing_plan_execution_runs_project_id",
        "marketing_plan_execution_runs",
        ["project_id"],
    )
    op.create_index(
        "ix_marketing_plan_execution_runs_marketing_plan_id",
        "marketing_plan_execution_runs",
        ["marketing_plan_id"],
    )
    op.create_index(
        "ix_marketing_plan_execution_runs_status",
        "marketing_plan_execution_runs",
        ["status"],
    )
    op.create_index(
        "ix_marketing_plan_execution_runs_created_at",
        "marketing_plan_execution_runs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_marketing_plan_execution_runs_created_at",
        table_name="marketing_plan_execution_runs",
    )
    op.drop_index(
        "ix_marketing_plan_execution_runs_status",
        table_name="marketing_plan_execution_runs",
    )
    op.drop_index(
        "ix_marketing_plan_execution_runs_marketing_plan_id",
        table_name="marketing_plan_execution_runs",
    )
    op.drop_index(
        "ix_marketing_plan_execution_runs_project_id",
        table_name="marketing_plan_execution_runs",
    )
    op.drop_index(
        "ix_marketing_plan_execution_runs_owner_id",
        table_name="marketing_plan_execution_runs",
    )
    op.drop_table("marketing_plan_execution_runs")
