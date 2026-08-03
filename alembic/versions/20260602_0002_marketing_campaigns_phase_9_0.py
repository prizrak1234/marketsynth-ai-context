"""Marketing campaigns skeleton (Phase 9.0).

Revision ID: 20260602_0002
Revises: 20260602_0001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_0002"
down_revision: Union[str, None] = "20260602_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("brief_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("campaign_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["brief_id"], ["marketing_briefs.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_campaigns_owner_id", "marketing_campaigns", ["owner_id"])
    op.create_index("ix_marketing_campaigns_project_id", "marketing_campaigns", ["project_id"])
    op.create_index("ix_marketing_campaigns_brief_id", "marketing_campaigns", ["brief_id"])
    op.create_index("ix_marketing_campaigns_status", "marketing_campaigns", ["status"])
    op.create_index("ix_marketing_campaigns_created_at", "marketing_campaigns", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_marketing_campaigns_created_at", table_name="marketing_campaigns")
    op.drop_index("ix_marketing_campaigns_status", table_name="marketing_campaigns")
    op.drop_index("ix_marketing_campaigns_brief_id", table_name="marketing_campaigns")
    op.drop_index("ix_marketing_campaigns_project_id", table_name="marketing_campaigns")
    op.drop_index("ix_marketing_campaigns_owner_id", table_name="marketing_campaigns")
    op.drop_table("marketing_campaigns")

