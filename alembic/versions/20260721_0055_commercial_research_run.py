"""Alembic: Phase 1B.1 commercial research orchestration run."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0055"
down_revision: Union[str, None] = "20260721_0054"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_research_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("user_request_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("project_brief_id", sa.Uuid(), nullable=False),
        sa.Column("project_brief_version", sa.Integer(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_stage", sa.String(length=32), nullable=False),
        sa.Column("completed_stages", sa.JSON(), nullable=False),
        sa.Column("progress_pct", sa.Integer(), nullable=False),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("run_version", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("preflight_json", sa.JSON(), nullable=False),
        sa.Column("quote_json", sa.JSON(), nullable=True),
        sa.Column("approval_json", sa.JSON(), nullable=True),
        sa.Column("provider_operation_id", sa.String(length=256), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("safe_error_message", sa.String(length=2000), nullable=True),
        sa.Column("outcome_unknown", sa.Boolean(), nullable=False),
        sa.Column("retry_blocked", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["project_brief_id"], ["project_briefs.id"]),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id",
            "user_request_id",
            "request_hash",
            name="uq_commercial_research_owner_request_hash",
        ),
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_commercial_research_owner_idempotency",
        ),
    )
    op.create_index(
        "ix_commercial_research_runs_owner",
        "commercial_research_runs",
        ["owner_id"],
    )
    op.create_index(
        "ix_commercial_research_runs_user_request",
        "commercial_research_runs",
        ["user_request_id"],
    )
    op.create_index(
        "ix_commercial_research_runs_status",
        "commercial_research_runs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_commercial_research_runs_status", table_name="commercial_research_runs")
    op.drop_index(
        "ix_commercial_research_runs_user_request",
        table_name="commercial_research_runs",
    )
    op.drop_index("ix_commercial_research_runs_owner", table_name="commercial_research_runs")
    op.drop_table("commercial_research_runs")
