"""Agent run parent hierarchy for sub-agent execution (Phase AI.11).

Revision ID: 20260602_0006
Revises: 20260602_0005
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_0006"
down_revision: Union[str, None] = "20260602_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("parent_agent_run_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_agent_runs_parent_agent_run_id",
        "agent_runs",
        "agent_runs",
        ["parent_agent_run_id"],
        ["id"],
    )
    op.create_index(
        "ix_agent_runs_parent_agent_run_id",
        "agent_runs",
        ["parent_agent_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_runs_parent_agent_run_id", table_name="agent_runs")
    op.drop_constraint("fk_agent_runs_parent_agent_run_id", "agent_runs", type_="foreignkey")
    op.drop_column("agent_runs", "parent_agent_run_id")
