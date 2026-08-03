"""BIV fetch ledger for research pipeline hardening."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0063"
down_revision: Union[str, None] = "20260728_0062"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "biv_fetch_ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("query_id", sa.String(length=128), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("normalized_url", sa.String(length=2048), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("outcome_code", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("error_class", sa.String(length=64), nullable=True),
        sa.Column("safe_error_message", sa.String(length=500), nullable=True),
        sa.Column("raw_content_stored", sa.Boolean(), nullable=False),
        sa.Column("extracted_text_length", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["business_idea_validation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_biv_fetch_ledger_run", "biv_fetch_ledger_entries", ["run_id"])
    op.create_index(
        "ix_biv_fetch_ledger_correlation",
        "biv_fetch_ledger_entries",
        ["correlation_id"],
    )
    op.create_index(
        "ix_biv_fetch_ledger_normalized_url",
        "biv_fetch_ledger_entries",
        ["run_id", "normalized_url"],
    )


def downgrade() -> None:
    op.drop_index("ix_biv_fetch_ledger_normalized_url", table_name="biv_fetch_ledger_entries")
    op.drop_index("ix_biv_fetch_ledger_correlation", table_name="biv_fetch_ledger_entries")
    op.drop_index("ix_biv_fetch_ledger_run", table_name="biv_fetch_ledger_entries")
    op.drop_table("biv_fetch_ledger_entries")
