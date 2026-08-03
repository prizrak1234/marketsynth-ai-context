"""Alembic: PRODUCT-01.3A BIV analysis context intake gate."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.migration_helpers import column_exists, index_exists, table_exists

revision: str = "20260724_0060"
down_revision: Union[str, None] = "20260724_0059"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not table_exists("analysis_contexts"):
        op.create_table(
            "analysis_contexts",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False),
            sa.Column("tenant_id", sa.Uuid(), nullable=False),
            sa.Column("project_id", sa.Uuid(), nullable=False),
            sa.Column("state", sa.String(length=32), nullable=False),
            sa.Column("source_mode", sa.String(length=32), nullable=True),
            sa.Column("data_source_label", sa.String(length=32), nullable=True),
            sa.Column("idea_description", sa.String(length=8000), nullable=False, server_default=""),
            sa.Column("product_or_service", sa.String(length=2000), nullable=True),
            sa.Column("target_customer", sa.String(length=2000), nullable=True),
            sa.Column("geography", sa.String(length=500), nullable=True),
            sa.Column("business_model", sa.String(length=1000), nullable=True),
            sa.Column("pricing_or_revenue_model", sa.String(length=1000), nullable=True),
            sa.Column("current_stage", sa.String(length=500), nullable=True),
            sa.Column("budget_context", sa.String(length=500), nullable=True),
            sa.Column("known_competitors", sa.String(length=2000), nullable=True),
            sa.Column("analysis_goal", sa.String(length=1000), nullable=True),
            sa.Column("target_customer_unknown", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("geography_unknown", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("confirmed_by_user", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("input_snapshot_hash", sa.String(length=64), nullable=True),
            sa.Column("source_snapshot_id", sa.Uuid(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.ForeignKeyConstraint(["source_snapshot_id"], ["analysis_contexts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not index_exists("analysis_contexts", "ix_analysis_context_owner_project"):
        op.create_index(
            "ix_analysis_context_owner_project",
            "analysis_contexts",
            ["owner_id", "project_id"],
        )
    if not index_exists("analysis_contexts", "ix_analysis_context_project_active"):
        op.create_index(
            "ix_analysis_context_project_active",
            "analysis_contexts",
            ["project_id", "is_active"],
        )

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        if not column_exists("business_idea_validation_runs", "analysis_context_id"):
            with op.batch_alter_table("business_idea_validation_runs") as batch_op:
                batch_op.add_column(sa.Column("analysis_context_id", sa.Uuid(), nullable=True))
                batch_op.add_column(sa.Column("input_snapshot_hash", sa.String(length=64), nullable=True))
                batch_op.create_foreign_key(
                    "fk_biv_runs_analysis_context",
                    "analysis_contexts",
                    ["analysis_context_id"],
                    ["id"],
                )
    else:
        if not column_exists("business_idea_validation_runs", "analysis_context_id"):
            op.add_column(
                "business_idea_validation_runs",
                sa.Column("analysis_context_id", sa.Uuid(), nullable=True),
            )
        if not column_exists("business_idea_validation_runs", "input_snapshot_hash"):
            op.add_column(
                "business_idea_validation_runs",
                sa.Column("input_snapshot_hash", sa.String(length=64), nullable=True),
            )
        if column_exists("business_idea_validation_runs", "analysis_context_id"):
            op.create_foreign_key(
                "fk_biv_runs_analysis_context",
                "business_idea_validation_runs",
                "analysis_contexts",
                ["analysis_context_id"],
                ["id"],
            )


def downgrade() -> None:
    op.drop_constraint("fk_biv_runs_analysis_context", "business_idea_validation_runs", type_="foreignkey")
    op.drop_column("business_idea_validation_runs", "input_snapshot_hash")
    op.drop_column("business_idea_validation_runs", "analysis_context_id")
    op.drop_index("ix_analysis_context_project_active", table_name="analysis_contexts")
    op.drop_index("ix_analysis_context_owner_project", table_name="analysis_contexts")
    op.drop_table("analysis_contexts")
