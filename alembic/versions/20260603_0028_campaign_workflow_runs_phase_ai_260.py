"""Campaign workflow runs table (Phase AI.260).

Revision ID: 20260603_0028
Revises: 20260603_0027
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0028"
down_revision: Union[str, None] = "20260603_0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_workflow_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("step_results", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaign_workflow_runs_owner_id", "campaign_workflow_runs", ["owner_id"])
    op.create_index("ix_campaign_workflow_runs_project_id", "campaign_workflow_runs", ["project_id"])
    op.create_index(
        "ix_campaign_workflow_runs_campaign_id",
        "campaign_workflow_runs",
        ["campaign_id"],
    )
    op.create_index(
        "ix_campaign_workflow_runs_template_id",
        "campaign_workflow_runs",
        ["template_id"],
    )
    op.create_index("ix_campaign_workflow_runs_status", "campaign_workflow_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_campaign_workflow_runs_status", table_name="campaign_workflow_runs")
    op.drop_index("ix_campaign_workflow_runs_template_id", table_name="campaign_workflow_runs")
    op.drop_index("ix_campaign_workflow_runs_campaign_id", table_name="campaign_workflow_runs")
    op.drop_index("ix_campaign_workflow_runs_project_id", table_name="campaign_workflow_runs")
    op.drop_index("ix_campaign_workflow_runs_owner_id", table_name="campaign_workflow_runs")
    op.drop_table("campaign_workflow_runs")
