"""Campaign brief intake table (Phase AI.211).

Revision ID: 20260603_0025
Revises: 20260603_0024
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0025"
down_revision: Union[str, None] = "20260603_0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_briefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column("source_intent", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("source_scenario_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("business_name", sa.String(length=256), nullable=True),
        sa.Column("industry", sa.String(length=128), nullable=True),
        sa.Column("offer", sa.String(length=4096), nullable=True),
        sa.Column("target_audience", sa.String(length=4096), nullable=True),
        sa.Column("geography", sa.String(length=512), nullable=True),
        sa.Column("channels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("budget_range", sa.String(length=256), nullable=True),
        sa.Column("deadline", sa.String(length=256), nullable=True),
        sa.Column("constraints", sa.String(length=4096), nullable=True),
        sa.Column("success_metric", sa.String(length=512), nullable=True),
        sa.Column("goal", sa.String(length=128), nullable=True),
        sa.Column("completeness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaign_briefs_owner_id", "campaign_briefs", ["owner_id"])
    op.create_index("ix_campaign_briefs_project_id", "campaign_briefs", ["project_id"])
    op.create_index("ix_campaign_briefs_campaign_id", "campaign_briefs", ["campaign_id"])
    op.create_index("ix_campaign_briefs_status", "campaign_briefs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_campaign_briefs_status", table_name="campaign_briefs")
    op.drop_index("ix_campaign_briefs_campaign_id", table_name="campaign_briefs")
    op.drop_index("ix_campaign_briefs_project_id", table_name="campaign_briefs")
    op.drop_index("ix_campaign_briefs_owner_id", table_name="campaign_briefs")
    op.drop_table("campaign_briefs")
