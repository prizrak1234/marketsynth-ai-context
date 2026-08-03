"""Marketing specialist outputs + versions (Phase AI.30).

Revision ID: 20260603_0011
Revises: 20260603_0010
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0011"
down_revision: Union[str, None] = "20260603_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_specialist_outputs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("marketing_plan_id", sa.Uuid(), nullable=False),
        sa.Column("execution_run_id", sa.Uuid(), nullable=False),
        sa.Column("task_index", sa.Integer(), nullable=False),
        sa.Column("specialist", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("output_type", sa.String(length=64), nullable=False),
        sa.Column("content", sa.String(length=8192), nullable=False),
        sa.Column("structured_data", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("approved_version_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["execution_run_id"], ["marketing_plan_execution_runs.id"]),
        sa.ForeignKeyConstraint(["marketing_plan_id"], ["marketing_plans.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "execution_run_id",
            "task_index",
            name="uq_marketing_specialist_outputs_run_task",
        ),
    )
    op.create_index(
        "ix_marketing_specialist_outputs_owner_id",
        "marketing_specialist_outputs",
        ["owner_id"],
    )
    op.create_index(
        "ix_marketing_specialist_outputs_project_id",
        "marketing_specialist_outputs",
        ["project_id"],
    )
    op.create_index(
        "ix_marketing_specialist_outputs_marketing_plan_id",
        "marketing_specialist_outputs",
        ["marketing_plan_id"],
    )
    op.create_index(
        "ix_marketing_specialist_outputs_execution_run_id",
        "marketing_specialist_outputs",
        ["execution_run_id"],
    )
    op.create_index(
        "ix_marketing_specialist_outputs_specialist",
        "marketing_specialist_outputs",
        ["specialist"],
    )
    op.create_index(
        "ix_marketing_specialist_outputs_status",
        "marketing_specialist_outputs",
        ["status"],
    )
    op.create_index(
        "ix_marketing_specialist_outputs_created_at",
        "marketing_specialist_outputs",
        ["created_at"],
    )

    op.create_table(
        "marketing_specialist_output_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("specialist_output_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("output_type", sa.String(length=64), nullable=False),
        sa.Column("content", sa.String(length=8192), nullable=False),
        sa.Column("structured_data", sa.JSON(), nullable=True),
        sa.Column("created_by_run_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_run_id"],
            ["marketing_plan_execution_runs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["specialist_output_id"],
            ["marketing_specialist_outputs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "specialist_output_id",
            "version_number",
            name="uq_marketing_specialist_output_versions_output_version",
        ),
    )
    op.create_index(
        "ix_marketing_specialist_output_versions_specialist_output_id",
        "marketing_specialist_output_versions",
        ["specialist_output_id"],
    )
    op.create_index(
        "ix_marketing_specialist_output_versions_created_at",
        "marketing_specialist_output_versions",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_marketing_specialist_output_versions_created_at",
        table_name="marketing_specialist_output_versions",
    )
    op.drop_index(
        "ix_marketing_specialist_output_versions_specialist_output_id",
        table_name="marketing_specialist_output_versions",
    )
    op.drop_table("marketing_specialist_output_versions")
    op.drop_index(
        "ix_marketing_specialist_outputs_created_at",
        table_name="marketing_specialist_outputs",
    )
    op.drop_index(
        "ix_marketing_specialist_outputs_status",
        table_name="marketing_specialist_outputs",
    )
    op.drop_index(
        "ix_marketing_specialist_outputs_specialist",
        table_name="marketing_specialist_outputs",
    )
    op.drop_index(
        "ix_marketing_specialist_outputs_execution_run_id",
        table_name="marketing_specialist_outputs",
    )
    op.drop_index(
        "ix_marketing_specialist_outputs_marketing_plan_id",
        table_name="marketing_specialist_outputs",
    )
    op.drop_index(
        "ix_marketing_specialist_outputs_project_id",
        table_name="marketing_specialist_outputs",
    )
    op.drop_index(
        "ix_marketing_specialist_outputs_owner_id",
        table_name="marketing_specialist_outputs",
    )
    op.drop_table("marketing_specialist_outputs")
