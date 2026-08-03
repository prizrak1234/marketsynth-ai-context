"""LLM request/response logging schema migration."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0005"
down_revision: Union[str, None] = "20260529_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_llm_responses_request_id", table_name="llm_responses")
    op.drop_table("llm_responses")
    op.drop_index("ix_llm_requests_task_id", table_name="llm_requests")
    op.drop_table("llm_requests")

    op.create_table(
        "llm_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("prompt_metadata", sa.JSON(), nullable=False),
        sa.Column("request_metadata", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_requests_owner_id", "llm_requests", ["owner_id"], unique=False)
    op.create_index("ix_llm_requests_project_id", "llm_requests", ["project_id"], unique=False)
    op.create_index("ix_llm_requests_agent_id", "llm_requests", ["agent_id"], unique=False)
    op.create_index("ix_llm_requests_agent_run_id", "llm_requests", ["agent_run_id"], unique=False)
    op.create_index("ix_llm_requests_task_id", "llm_requests", ["task_id"], unique=False)
    op.create_index("ix_llm_requests_status", "llm_requests", ["status"], unique=False)
    op.create_index("ix_llm_requests_provider", "llm_requests", ["provider"], unique=False)
    op.create_index("ix_llm_requests_model", "llm_requests", ["model"], unique=False)
    op.create_index("ix_llm_requests_created_at", "llm_requests", ["created_at"], unique=False)

    op.create_table(
        "llm_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("llm_request_id", sa.Uuid(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=False),
        sa.Column("raw_response", sa.JSON(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_estimate", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("response_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["llm_request_id"], ["llm_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("llm_request_id", name="uq_llm_responses_llm_request_id"),
    )
    op.create_index(
        "ix_llm_responses_llm_request_id",
        "llm_responses",
        ["llm_request_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_llm_responses_llm_request_id", table_name="llm_responses")
    op.drop_table("llm_responses")
    op.drop_index("ix_llm_requests_created_at", table_name="llm_requests")
    op.drop_index("ix_llm_requests_model", table_name="llm_requests")
    op.drop_index("ix_llm_requests_provider", table_name="llm_requests")
    op.drop_index("ix_llm_requests_status", table_name="llm_requests")
    op.drop_index("ix_llm_requests_task_id", table_name="llm_requests")
    op.drop_index("ix_llm_requests_agent_run_id", table_name="llm_requests")
    op.drop_index("ix_llm_requests_agent_id", table_name="llm_requests")
    op.drop_index("ix_llm_requests_project_id", table_name="llm_requests")
    op.drop_index("ix_llm_requests_owner_id", table_name="llm_requests")
    op.drop_table("llm_requests")

    op.create_table(
        "llm_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("messages", sa.JSON(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_requests_task_id", "llm_requests", ["task_id"], unique=False)

    op.create_table(
        "llm_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("usage", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["llm_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_responses_request_id", "llm_responses", ["request_id"], unique=False)
