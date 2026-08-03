"""Campaign plan drafts (Phase 10.1).

Revision ID: 20260602_0004
Revises: 20260602_0003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_0004"
down_revision: Union[str, None] = "20260602_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_plan_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("source_agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("plan_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["source_agent_run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaign_plan_drafts_owner_id", "campaign_plan_drafts", ["owner_id"])
    op.create_index("ix_campaign_plan_drafts_project_id", "campaign_plan_drafts", ["project_id"])
    op.create_index(
        "ix_campaign_plan_drafts_campaign_id",
        "campaign_plan_drafts",
        ["campaign_id"],
    )
    op.create_index("ix_campaign_plan_drafts_status", "campaign_plan_drafts", ["status"])
    op.create_index(
        "ix_campaign_plan_drafts_created_at",
        "campaign_plan_drafts",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_campaign_plan_drafts_created_at", table_name="campaign_plan_drafts")
    op.drop_index("ix_campaign_plan_drafts_status", table_name="campaign_plan_drafts")
    op.drop_index("ix_campaign_plan_drafts_campaign_id", table_name="campaign_plan_drafts")
    op.drop_index("ix_campaign_plan_drafts_project_id", table_name="campaign_plan_drafts")
    op.drop_index("ix_campaign_plan_drafts_owner_id", table_name="campaign_plan_drafts")
    op.drop_table("campaign_plan_drafts")
