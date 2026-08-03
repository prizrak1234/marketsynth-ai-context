"""Partial unique index: one active BIV run per project (RUNTIME-01G)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0065"
down_revision: Union[str, None] = "20260730_0064"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_biv_one_active_run_per_project",
        "business_idea_validation_runs",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
        sqlite_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_biv_one_active_run_per_project",
        table_name="business_idea_validation_runs",
    )
