"""Append-only ProjectBrief table (Commercial MVP P0.1).

Revision ID: 20260614_0029
Revises: 20260603_0028
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0029"
down_revision: Union[str, None] = "20260603_0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_briefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("project_basics", sa.JSON(), nullable=False),
        sa.Column("product", sa.JSON(), nullable=False),
        sa.Column("market", sa.JSON(), nullable=False),
        sa.Column("audience", sa.JSON(), nullable=False),
        sa.Column("economics", sa.JSON(), nullable=False),
        sa.Column("materials_summary", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("missing_data", sa.JSON(), nullable=False),
        sa.Column("readiness_status", sa.String(length=32), nullable=False),
        sa.Column("readiness_reasons", sa.JSON(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("supersedes_brief_id", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["supersedes_brief_id"], ["project_briefs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "version",
            name="uq_project_briefs_project_version",
        ),
    )
    op.create_index("ix_project_briefs_owner_id", "project_briefs", ["owner_id"])
    op.create_index("ix_project_briefs_project_id", "project_briefs", ["project_id"])
    op.create_index(
        "ix_project_briefs_project_id_status",
        "project_briefs",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_project_briefs_input_fingerprint",
        "project_briefs",
        ["input_fingerprint"],
    )
    op.create_index("ix_project_briefs_created_at", "project_briefs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_project_briefs_created_at", table_name="project_briefs")
    op.drop_index("ix_project_briefs_input_fingerprint", table_name="project_briefs")
    op.drop_index("ix_project_briefs_project_id_status", table_name="project_briefs")
    op.drop_index("ix_project_briefs_project_id", table_name="project_briefs")
    op.drop_index("ix_project_briefs_owner_id", table_name="project_briefs")
    op.drop_table("project_briefs")
