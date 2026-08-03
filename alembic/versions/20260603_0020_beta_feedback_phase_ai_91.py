"""Beta feedback reports (AI.91).

Revision ID: 20260603_0020
Revises: 20260603_0019
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0020"
down_revision: Union[str, None] = "20260603_0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "beta_feedback_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("safe_context", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_beta_feedback_reports_owner_id",
        "beta_feedback_reports",
        ["owner_id"],
    )
    op.create_index(
        "ix_beta_feedback_reports_project_id",
        "beta_feedback_reports",
        ["project_id"],
    )
    op.create_index(
        "ix_beta_feedback_reports_status",
        "beta_feedback_reports",
        ["status"],
    )
    op.create_index(
        "ix_beta_feedback_reports_source",
        "beta_feedback_reports",
        ["source"],
    )
    op.create_index(
        "ix_beta_feedback_reports_severity",
        "beta_feedback_reports",
        ["severity"],
    )
    op.create_index(
        "ix_beta_feedback_reports_created_at",
        "beta_feedback_reports",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_beta_feedback_reports_created_at", table_name="beta_feedback_reports")
    op.drop_index("ix_beta_feedback_reports_severity", table_name="beta_feedback_reports")
    op.drop_index("ix_beta_feedback_reports_source", table_name="beta_feedback_reports")
    op.drop_index("ix_beta_feedback_reports_status", table_name="beta_feedback_reports")
    op.drop_index("ix_beta_feedback_reports_project_id", table_name="beta_feedback_reports")
    op.drop_index("ix_beta_feedback_reports_owner_id", table_name="beta_feedback_reports")
    op.drop_table("beta_feedback_reports")
