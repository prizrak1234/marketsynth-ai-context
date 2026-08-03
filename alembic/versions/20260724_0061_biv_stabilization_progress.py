"""BIV stabilization — progress, observability, lineage columns on runs."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.migration_helpers import column_exists

revision: str = "20260724_0061"
down_revision: Union[str, None] = "20260724_0060"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not column_exists("business_idea_validation_runs", "parent_run_id"):
        op.add_column(
            "business_idea_validation_runs",
            sa.Column("parent_run_id", sa.Uuid(), nullable=True),
        )
    if not column_exists("business_idea_validation_runs", "research_mode"):
        op.add_column(
            "business_idea_validation_runs",
            sa.Column("research_mode", sa.String(length=32), nullable=True),
        )
    if not column_exists("business_idea_validation_runs", "progress_json"):
        op.add_column(
            "business_idea_validation_runs",
            sa.Column("progress_json", sa.JSON(), nullable=True),
        )
    if not column_exists("business_idea_validation_runs", "observability_json"):
        op.add_column(
            "business_idea_validation_runs",
            sa.Column("observability_json", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    if column_exists("business_idea_validation_runs", "observability_json"):
        op.drop_column("business_idea_validation_runs", "observability_json")
    if column_exists("business_idea_validation_runs", "progress_json"):
        op.drop_column("business_idea_validation_runs", "progress_json")
    if column_exists("business_idea_validation_runs", "research_mode"):
        op.drop_column("business_idea_validation_runs", "research_mode")
    if column_exists("business_idea_validation_runs", "parent_run_id"):
        op.drop_column("business_idea_validation_runs", "parent_run_id")
