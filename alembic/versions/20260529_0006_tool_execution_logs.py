"""Tool execution audit log schema migration."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0006"
down_revision: Union[str, None] = "20260529_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tool_execution_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("llm_request_id", sa.Uuid(), nullable=True),
        sa.Column("tool_call_id", sa.String(length=128), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("execution_mode", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("arguments_preview", sa.JSON(), nullable=False),
        sa.Column("result_preview", sa.JSON(), nullable=False),
        sa.Column("error_payload", sa.JSON(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["llm_request_id"], ["llm_requests.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tool_execution_logs_owner_id",
        "tool_execution_logs",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_execution_logs_project_id",
        "tool_execution_logs",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_execution_logs_agent_run_id",
        "tool_execution_logs",
        ["agent_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_execution_logs_agent_id",
        "tool_execution_logs",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_execution_logs_tool_name",
        "tool_execution_logs",
        ["tool_name"],
        unique=False,
    )
    op.create_index(
        "ix_tool_execution_logs_status",
        "tool_execution_logs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_tool_execution_logs_created_at",
        "tool_execution_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_tool_execution_logs_llm_request_id",
        "tool_execution_logs",
        ["llm_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_execution_logs_task_id",
        "tool_execution_logs",
        ["task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tool_execution_logs_task_id", table_name="tool_execution_logs")
    op.drop_index("ix_tool_execution_logs_llm_request_id", table_name="tool_execution_logs")
    op.drop_index("ix_tool_execution_logs_created_at", table_name="tool_execution_logs")
    op.drop_index("ix_tool_execution_logs_status", table_name="tool_execution_logs")
    op.drop_index("ix_tool_execution_logs_tool_name", table_name="tool_execution_logs")
    op.drop_index("ix_tool_execution_logs_agent_id", table_name="tool_execution_logs")
    op.drop_index("ix_tool_execution_logs_agent_run_id", table_name="tool_execution_logs")
    op.drop_index("ix_tool_execution_logs_project_id", table_name="tool_execution_logs")
    op.drop_index("ix_tool_execution_logs_owner_id", table_name="tool_execution_logs")
    op.drop_table("tool_execution_logs")
