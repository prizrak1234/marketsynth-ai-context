"""Marketing funnels, steps, and asset links (Phase 4.8).

Revision ID: 20260529_0014
Revises: 20260529_0013
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0014"
down_revision: Union[str, None] = "20260529_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_funnels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("brief_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["brief_id"], ["marketing_briefs.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_funnels_owner_id", "marketing_funnels", ["owner_id"])
    op.create_index("ix_marketing_funnels_project_id", "marketing_funnels", ["project_id"])
    op.create_index("ix_marketing_funnels_brief_id", "marketing_funnels", ["brief_id"])
    op.create_index("ix_marketing_funnels_status", "marketing_funnels", ["status"])
    op.create_index("ix_marketing_funnels_created_at", "marketing_funnels", ["created_at"])

    op.create_table(
        "marketing_funnel_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("funnel_id", sa.Uuid(), nullable=False),
        sa.Column("step_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["funnel_id"], ["marketing_funnels.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("funnel_id", "position", name="uq_marketing_funnel_steps_funnel_position"),
    )
    op.create_index("ix_marketing_funnel_steps_owner_id", "marketing_funnel_steps", ["owner_id"])
    op.create_index(
        "ix_marketing_funnel_steps_project_id",
        "marketing_funnel_steps",
        ["project_id"],
    )
    op.create_index(
        "ix_marketing_funnel_steps_funnel_id",
        "marketing_funnel_steps",
        ["funnel_id"],
    )
    op.create_index(
        "ix_marketing_funnel_steps_step_type",
        "marketing_funnel_steps",
        ["step_type"],
    )
    op.create_index(
        "ix_marketing_funnel_steps_position",
        "marketing_funnel_steps",
        ["position"],
    )
    op.create_index("ix_marketing_funnel_steps_status", "marketing_funnel_steps", ["status"])

    op.create_table(
        "funnel_step_asset_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("funnel_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="primary"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["content_assets.id"]),
        sa.ForeignKeyConstraint(["funnel_id"], ["marketing_funnels.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["step_id"], ["marketing_funnel_steps.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_funnel_step_asset_links_owner_id",
        "funnel_step_asset_links",
        ["owner_id"],
    )
    op.create_index(
        "ix_funnel_step_asset_links_project_id",
        "funnel_step_asset_links",
        ["project_id"],
    )
    op.create_index(
        "ix_funnel_step_asset_links_funnel_id",
        "funnel_step_asset_links",
        ["funnel_id"],
    )
    op.create_index(
        "ix_funnel_step_asset_links_step_id",
        "funnel_step_asset_links",
        ["step_id"],
    )
    op.create_index(
        "ix_funnel_step_asset_links_asset_id",
        "funnel_step_asset_links",
        ["asset_id"],
    )
    op.create_index(
        "ix_funnel_step_asset_links_role",
        "funnel_step_asset_links",
        ["role"],
    )


def downgrade() -> None:
    op.drop_index("ix_funnel_step_asset_links_role", table_name="funnel_step_asset_links")
    op.drop_index("ix_funnel_step_asset_links_asset_id", table_name="funnel_step_asset_links")
    op.drop_index("ix_funnel_step_asset_links_step_id", table_name="funnel_step_asset_links")
    op.drop_index("ix_funnel_step_asset_links_funnel_id", table_name="funnel_step_asset_links")
    op.drop_index("ix_funnel_step_asset_links_project_id", table_name="funnel_step_asset_links")
    op.drop_index("ix_funnel_step_asset_links_owner_id", table_name="funnel_step_asset_links")
    op.drop_table("funnel_step_asset_links")

    op.drop_index("ix_marketing_funnel_steps_status", table_name="marketing_funnel_steps")
    op.drop_index("ix_marketing_funnel_steps_position", table_name="marketing_funnel_steps")
    op.drop_index("ix_marketing_funnel_steps_step_type", table_name="marketing_funnel_steps")
    op.drop_index("ix_marketing_funnel_steps_funnel_id", table_name="marketing_funnel_steps")
    op.drop_index("ix_marketing_funnel_steps_project_id", table_name="marketing_funnel_steps")
    op.drop_index("ix_marketing_funnel_steps_owner_id", table_name="marketing_funnel_steps")
    op.drop_table("marketing_funnel_steps")

    op.drop_index("ix_marketing_funnels_created_at", table_name="marketing_funnels")
    op.drop_index("ix_marketing_funnels_status", table_name="marketing_funnels")
    op.drop_index("ix_marketing_funnels_brief_id", table_name="marketing_funnels")
    op.drop_index("ix_marketing_funnels_project_id", table_name="marketing_funnels")
    op.drop_index("ix_marketing_funnels_owner_id", table_name="marketing_funnels")
    op.drop_table("marketing_funnels")
