"""Chat audit events (Phase AI.25).

Revision ID: 20260603_0008
Revises: 20260603_0007
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0008"
down_revision: Union[str, None] = "20260603_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("entrypoint", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("safe_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["agent_chat_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_audit_events_owner_id", "chat_audit_events", ["owner_id"])
    op.create_index("ix_chat_audit_events_project_id", "chat_audit_events", ["project_id"])
    op.create_index("ix_chat_audit_events_session_id", "chat_audit_events", ["session_id"])
    op.create_index("ix_chat_audit_events_message_id", "chat_audit_events", ["message_id"])
    op.create_index("ix_chat_audit_events_agent_id", "chat_audit_events", ["agent_id"])
    op.create_index("ix_chat_audit_events_event_type", "chat_audit_events", ["event_type"])
    op.create_index("ix_chat_audit_events_status", "chat_audit_events", ["status"])
    op.create_index("ix_chat_audit_events_created_at", "chat_audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_audit_events_created_at", table_name="chat_audit_events")
    op.drop_index("ix_chat_audit_events_status", table_name="chat_audit_events")
    op.drop_index("ix_chat_audit_events_event_type", table_name="chat_audit_events")
    op.drop_index("ix_chat_audit_events_agent_id", table_name="chat_audit_events")
    op.drop_index("ix_chat_audit_events_message_id", table_name="chat_audit_events")
    op.drop_index("ix_chat_audit_events_session_id", table_name="chat_audit_events")
    op.drop_index("ix_chat_audit_events_project_id", table_name="chat_audit_events")
    op.drop_index("ix_chat_audit_events_owner_id", table_name="chat_audit_events")
    op.drop_table("chat_audit_events")
