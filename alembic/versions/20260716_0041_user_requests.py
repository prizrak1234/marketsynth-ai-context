"""User requests table (Phase H1 conversational intake).

Revision ID: 20260716_0041
Revises: 20260716_0040
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0041"
down_revision: Union[str, None] = "20260716_0040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(length=8000), nullable=False),
        sa.Column("normalized_text", sa.String(length=8000), nullable=False),
        sa.Column("selected_scenario", sa.String(length=64), nullable=True),
        sa.Column("route_category", sa.String(length=64), nullable=False),
        sa.Column("route_kind", sa.String(length=32), nullable=False),
        sa.Column("route_confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("clarification_question", sa.String(length=2000), nullable=True),
        sa.Column("clarification_answer", sa.String(length=4000), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_specialist", sa.String(length=64), nullable=True),
        sa.Column("requires_project", sa.Boolean(), nullable=False),
        sa.Column("avoids_investigation", sa.Boolean(), nullable=False),
        sa.Column("next_href", sa.String(length=512), nullable=True),
        sa.Column("next_action_label", sa.String(length=256), nullable=True),
        sa.Column("assistant_message", sa.String(length=4000), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_requests_owner_id", "user_requests", ["owner_id"])
    op.create_index("ix_user_requests_status", "user_requests", ["status"])
    op.create_index("ix_user_requests_route_category", "user_requests", ["route_category"])
    op.create_index("ix_user_requests_project_id", "user_requests", ["project_id"])
    op.create_index("ix_user_requests_task_id", "user_requests", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_user_requests_task_id", table_name="user_requests")
    op.drop_index("ix_user_requests_project_id", table_name="user_requests")
    op.drop_index("ix_user_requests_route_category", table_name="user_requests")
    op.drop_index("ix_user_requests_status", table_name="user_requests")
    op.drop_index("ix_user_requests_owner_id", table_name="user_requests")
    op.drop_table("user_requests")
