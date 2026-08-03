"""Alembic: CMVP.1 business idea validation + MCP tool call audit."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_0057"
down_revision: Union[str, None] = "20260721_0056"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mcp_tool_call_audits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_request_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=True),
        sa.Column("server_role", sa.String(length=32), nullable=False),
        sa.Column("server_id", sa.String(length=64), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("tool_schema_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("response_size_bytes", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("request_summary", sa.JSON(), nullable=False),
        sa.Column("response_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mcp_tool_call_audits_owner",
        "mcp_tool_call_audits",
        ["owner_id"],
    )
    op.create_index(
        "ix_mcp_tool_call_audits_user_request",
        "mcp_tool_call_audits",
        ["user_request_id"],
    )
    op.create_index(
        "ix_mcp_tool_call_audits_investigation",
        "mcp_tool_call_audits",
        ["investigation_id"],
    )

    op.create_table(
        "business_idea_validation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_request_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("business_verdict_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("safe_error_message", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.ForeignKeyConstraint(["business_verdict_id"], ["business_verdicts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_biv_runs_owner_idempotency",
        ),
    )
    op.create_index("ix_biv_runs_owner", "business_idea_validation_runs", ["owner_id"])
    op.create_index(
        "ix_biv_runs_user_request",
        "business_idea_validation_runs",
        ["user_request_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_biv_runs_user_request", table_name="business_idea_validation_runs")
    op.drop_index("ix_biv_runs_owner", table_name="business_idea_validation_runs")
    op.drop_table("business_idea_validation_runs")
    op.drop_index("ix_mcp_tool_call_audits_investigation", table_name="mcp_tool_call_audits")
    op.drop_index("ix_mcp_tool_call_audits_user_request", table_name="mcp_tool_call_audits")
    op.drop_index("ix_mcp_tool_call_audits_owner", table_name="mcp_tool_call_audits")
    op.drop_table("mcp_tool_call_audits")
