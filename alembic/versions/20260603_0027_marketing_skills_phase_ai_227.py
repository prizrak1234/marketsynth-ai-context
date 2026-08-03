"""Marketing skill runs table (Phase AI.227).

Revision ID: 20260603_0027
Revises: 20260603_0026
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0027"
down_revision: Union[str, None] = "20260603_0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_skill_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("skill_type", sa.String(length=64), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("used_tool_call_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("safe_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error", sa.String(length=512), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_skill_runs_owner_id", "marketing_skill_runs", ["owner_id"])
    op.create_index("ix_marketing_skill_runs_project_id", "marketing_skill_runs", ["project_id"])
    op.create_index("ix_marketing_skill_runs_campaign_id", "marketing_skill_runs", ["campaign_id"])
    op.create_index("ix_marketing_skill_runs_skill_type", "marketing_skill_runs", ["skill_type"])
    op.create_index("ix_marketing_skill_runs_status", "marketing_skill_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_marketing_skill_runs_status", table_name="marketing_skill_runs")
    op.drop_index("ix_marketing_skill_runs_skill_type", table_name="marketing_skill_runs")
    op.drop_index("ix_marketing_skill_runs_campaign_id", table_name="marketing_skill_runs")
    op.drop_index("ix_marketing_skill_runs_project_id", table_name="marketing_skill_runs")
    op.drop_index("ix_marketing_skill_runs_owner_id", table_name="marketing_skill_runs")
    op.drop_table("marketing_skill_runs")
