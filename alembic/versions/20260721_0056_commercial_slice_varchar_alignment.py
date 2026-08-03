"""Alembic: align stamped varchar widths for 0054/0055 tables (create_all drift)."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260721_0056"
down_revision: Union[str, None] = "20260721_0055"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent widen: safe whether table came from migration (32) or create_all (9/17/19).
    op.execute("ALTER TABLE video_clip_requests ALTER COLUMN status TYPE VARCHAR(32)")
    op.execute("ALTER TABLE commercial_research_runs ALTER COLUMN status TYPE VARCHAR(32)")
    op.execute(
        "ALTER TABLE commercial_research_runs ALTER COLUMN current_stage TYPE VARCHAR(32)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE video_clip_requests ALTER COLUMN status TYPE VARCHAR(9)")
    op.execute("ALTER TABLE commercial_research_runs ALTER COLUMN status TYPE VARCHAR(17)")
    op.execute(
        "ALTER TABLE commercial_research_runs ALTER COLUMN current_stage TYPE VARCHAR(19)"
    )
