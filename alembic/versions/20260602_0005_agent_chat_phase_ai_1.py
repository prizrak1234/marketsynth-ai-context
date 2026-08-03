"""Agent chat sessions and messages (Phase AI.1).

Revision ID: 20260602_0005
Revises: 20260602_0004
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_0005"
down_revision: Union[str, None] = "20260602_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_chat_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_chat_sessions_owner_id", "agent_chat_sessions", ["owner_id"])
    op.create_index("ix_agent_chat_sessions_project_id", "agent_chat_sessions", ["project_id"])
    op.create_index("ix_agent_chat_sessions_updated_at", "agent_chat_sessions", ["updated_at"])

    op.create_table(
        "agent_chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.String(length=65536), nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["agent_chat_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_chat_messages_session_id", "agent_chat_messages", ["session_id"])
    op.create_index("ix_agent_chat_messages_created_at", "agent_chat_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_chat_messages_created_at", table_name="agent_chat_messages")
    op.drop_index("ix_agent_chat_messages_session_id", table_name="agent_chat_messages")
    op.drop_table("agent_chat_messages")
    op.drop_index("ix_agent_chat_sessions_updated_at", table_name="agent_chat_sessions")
    op.drop_index("ix_agent_chat_sessions_project_id", table_name="agent_chat_sessions")
    op.drop_index("ix_agent_chat_sessions_owner_id", table_name="agent_chat_sessions")
    op.drop_table("agent_chat_sessions")
