"""Scenario wizard runs persistence (Phase AI.137).

Revision ID: 20260603_0023
Revises: 20260603_0022
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0023"
down_revision: Union[str, None] = "20260603_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scenario_wizard_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.String(length=128), nullable=False),
        sa.Column("scenario_name", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step", sa.String(length=64), nullable=False),
        sa.Column("step_results", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("failure_reason", sa.String(length=1024), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenario_wizard_runs_owner_id", "scenario_wizard_runs", ["owner_id"])
    op.create_index("ix_scenario_wizard_runs_project_id", "scenario_wizard_runs", ["project_id"])
    op.create_index("ix_scenario_wizard_runs_scenario_id", "scenario_wizard_runs", ["scenario_id"])
    op.create_index("ix_scenario_wizard_runs_status", "scenario_wizard_runs", ["status"])
    op.create_index("ix_scenario_wizard_runs_created_at", "scenario_wizard_runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_scenario_wizard_runs_created_at", table_name="scenario_wizard_runs")
    op.drop_index("ix_scenario_wizard_runs_status", table_name="scenario_wizard_runs")
    op.drop_index("ix_scenario_wizard_runs_scenario_id", table_name="scenario_wizard_runs")
    op.drop_index("ix_scenario_wizard_runs_project_id", table_name="scenario_wizard_runs")
    op.drop_index("ix_scenario_wizard_runs_owner_id", table_name="scenario_wizard_runs")
    op.drop_table("scenario_wizard_runs")
