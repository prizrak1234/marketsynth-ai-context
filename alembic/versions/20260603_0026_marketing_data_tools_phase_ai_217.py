"""Marketing tool calls table (Phase AI.217).

Revision ID: 20260603_0026
Revises: 20260603_0025
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0026"
down_revision: Union[str, None] = "20260603_0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_tool_calls",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("tool_type", sa.String(length=32), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("safe_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error", sa.String(length=512), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marketing_tool_calls_owner_id", "marketing_tool_calls", ["owner_id"])
    op.create_index("ix_marketing_tool_calls_project_id", "marketing_tool_calls", ["project_id"])
    op.create_index("ix_marketing_tool_calls_tool_type", "marketing_tool_calls", ["tool_type"])
    op.create_index("ix_marketing_tool_calls_status", "marketing_tool_calls", ["status"])


def downgrade() -> None:
    op.drop_index("ix_marketing_tool_calls_status", table_name="marketing_tool_calls")
    op.drop_index("ix_marketing_tool_calls_tool_type", table_name="marketing_tool_calls")
    op.drop_index("ix_marketing_tool_calls_project_id", table_name="marketing_tool_calls")
    op.drop_index("ix_marketing_tool_calls_owner_id", table_name="marketing_tool_calls")
    op.drop_table("marketing_tool_calls")
