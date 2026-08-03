"""Marketing plans + versions (Phase AI.28).

Revision ID: 20260603_0009
Revises: 20260603_0008
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0009"
down_revision: Union[str, None] = "20260603_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_run_id", sa.Uuid(), nullable=True),
        sa.Column("source_session_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("goal", sa.String(length=4096), nullable=False),
        sa.Column("project_context", sa.JSON(), nullable=True),
        sa.Column("specialist_tasks", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("execution_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("approved_version_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["source_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["source_session_id"], ["agent_chat_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_plans_owner_id", "marketing_plans", ["owner_id"])
    op.create_index("ix_marketing_plans_project_id", "marketing_plans", ["project_id"])
    op.create_index("ix_marketing_plans_status", "marketing_plans", ["status"])
    op.create_index("ix_marketing_plans_source_run_id", "marketing_plans", ["source_run_id"])
    op.create_index(
        "ix_marketing_plans_source_session_id",
        "marketing_plans",
        ["source_session_id"],
    )
    op.create_index("ix_marketing_plans_created_at", "marketing_plans", ["created_at"])

    op.create_table(
        "marketing_plan_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("marketing_plan_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("goal", sa.String(length=4096), nullable=False),
        sa.Column("project_context", sa.JSON(), nullable=True),
        sa.Column("specialist_tasks", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("execution_mode", sa.String(length=32), nullable=False),
        sa.Column("created_by_run_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["marketing_plan_id"], ["marketing_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "marketing_plan_id",
            "version_number",
            name="uq_marketing_plan_versions_plan_version",
        ),
    )
    op.create_index(
        "ix_marketing_plan_versions_marketing_plan_id",
        "marketing_plan_versions",
        ["marketing_plan_id"],
    )
    op.create_index(
        "ix_marketing_plan_versions_created_at",
        "marketing_plan_versions",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_plan_versions_created_at", table_name="marketing_plan_versions")
    op.drop_index(
        "ix_marketing_plan_versions_marketing_plan_id",
        table_name="marketing_plan_versions",
    )
    op.drop_table("marketing_plan_versions")
    op.drop_index("ix_marketing_plans_created_at", table_name="marketing_plans")
    op.drop_index("ix_marketing_plans_source_session_id", table_name="marketing_plans")
    op.drop_index("ix_marketing_plans_source_run_id", table_name="marketing_plans")
    op.drop_index("ix_marketing_plans_status", table_name="marketing_plans")
    op.drop_index("ix_marketing_plans_project_id", table_name="marketing_plans")
    op.drop_index("ix_marketing_plans_owner_id", table_name="marketing_plans")
    op.drop_table("marketing_plans")
