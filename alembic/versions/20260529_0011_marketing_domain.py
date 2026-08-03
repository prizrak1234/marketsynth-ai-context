"""Marketing briefs and content assets (Phase 4.0).

Revision ID: 20260529_0011
Revises: 20260529_0010
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0011"
down_revision: Union[str, None] = "20260529_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_briefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("product_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("target_audience", sa.Text(), nullable=False, server_default=""),
        sa.Column("offer", sa.Text(), nullable=False, server_default=""),
        sa.Column("goals", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("constraints", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_briefs_owner_id", "marketing_briefs", ["owner_id"])
    op.create_index("ix_marketing_briefs_project_id", "marketing_briefs", ["project_id"])
    op.create_index("ix_marketing_briefs_status", "marketing_briefs", ["status"])
    op.create_index("ix_marketing_briefs_created_at", "marketing_briefs", ["created_at"])

    op.create_table(
        "content_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("brief_id", sa.Uuid(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["brief_id"], ["marketing_briefs.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_assets_owner_id", "content_assets", ["owner_id"])
    op.create_index("ix_content_assets_project_id", "content_assets", ["project_id"])
    op.create_index("ix_content_assets_brief_id", "content_assets", ["brief_id"])
    op.create_index("ix_content_assets_task_id", "content_assets", ["task_id"])
    op.create_index("ix_content_assets_agent_run_id", "content_assets", ["agent_run_id"])
    op.create_index("ix_content_assets_asset_type", "content_assets", ["asset_type"])
    op.create_index("ix_content_assets_status", "content_assets", ["status"])
    op.create_index("ix_content_assets_created_at", "content_assets", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_content_assets_created_at", table_name="content_assets")
    op.drop_index("ix_content_assets_status", table_name="content_assets")
    op.drop_index("ix_content_assets_asset_type", table_name="content_assets")
    op.drop_index("ix_content_assets_agent_run_id", table_name="content_assets")
    op.drop_index("ix_content_assets_task_id", table_name="content_assets")
    op.drop_index("ix_content_assets_brief_id", table_name="content_assets")
    op.drop_index("ix_content_assets_project_id", table_name="content_assets")
    op.drop_index("ix_content_assets_owner_id", table_name="content_assets")
    op.drop_table("content_assets")

    op.drop_index("ix_marketing_briefs_created_at", table_name="marketing_briefs")
    op.drop_index("ix_marketing_briefs_status", table_name="marketing_briefs")
    op.drop_index("ix_marketing_briefs_project_id", table_name="marketing_briefs")
    op.drop_index("ix_marketing_briefs_owner_id", table_name="marketing_briefs")
    op.drop_table("marketing_briefs")
