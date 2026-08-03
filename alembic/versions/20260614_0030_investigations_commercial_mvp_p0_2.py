"""Append-only Investigation table (Commercial MVP P0.2).

Revision ID: 20260614_0030
Revises: 20260614_0029
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0030"
down_revision: Union[str, None] = "20260614_0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "investigations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("project_brief_id", sa.Uuid(), nullable=False),
        sa.Column("project_brief_version", sa.Integer(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("stages", sa.JSON(), nullable=False),
        sa.Column("readiness_status", sa.String(length=32), nullable=False),
        sa.Column("readiness_reasons", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("blocked_reason", sa.String(length=2000), nullable=True),
        sa.Column("supersedes_investigation_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["project_brief_id"], ["project_briefs.id"]),
        sa.ForeignKeyConstraint(["supersedes_investigation_id"], ["investigations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "version",
            name="uq_investigations_project_version",
        ),
    )
    op.create_index("ix_investigations_owner_id", "investigations", ["owner_id"])
    op.create_index("ix_investigations_project_id", "investigations", ["project_id"])
    op.create_index(
        "ix_investigations_project_brief_id",
        "investigations",
        ["project_brief_id"],
    )
    op.create_index(
        "ix_investigations_project_id_status",
        "investigations",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_investigations_project_id_current_stage",
        "investigations",
        ["project_id", "current_stage"],
    )
    op.create_index("ix_investigations_created_at", "investigations", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_investigations_created_at", table_name="investigations")
    op.drop_index(
        "ix_investigations_project_id_current_stage",
        table_name="investigations",
    )
    op.drop_index("ix_investigations_project_id_status", table_name="investigations")
    op.drop_index("ix_investigations_project_brief_id", table_name="investigations")
    op.drop_index("ix_investigations_project_id", table_name="investigations")
    op.drop_index("ix_investigations_owner_id", table_name="investigations")
    op.drop_table("investigations")
