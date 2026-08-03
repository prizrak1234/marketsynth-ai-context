"""Chat session entrypoint, domain, status, message metadata (Phase AI.19).

Revision ID: 20260603_0007
Revises: 20260602_0006
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0007"
down_revision: Union[str, None] = "20260602_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_chat_sessions",
        sa.Column("entrypoint", sa.String(length=32), nullable=False, server_default="direct_specialist"),
    )
    op.add_column(
        "agent_chat_sessions",
        sa.Column("domain", sa.String(length=32), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "agent_chat_sessions",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
    )
    op.create_index("ix_agent_chat_sessions_agent_id", "agent_chat_sessions", ["agent_id"])
    op.create_index("ix_agent_chat_sessions_status", "agent_chat_sessions", ["status"])

    op.add_column(
        "agent_chat_messages",
        sa.Column("message_metadata", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("agent_chat_messages", "message_metadata")
    op.drop_index("ix_agent_chat_sessions_status", table_name="agent_chat_sessions")
    op.drop_index("ix_agent_chat_sessions_agent_id", table_name="agent_chat_sessions")
    op.drop_column("agent_chat_sessions", "status")
    op.drop_column("agent_chat_sessions", "domain")
    op.drop_column("agent_chat_sessions", "entrypoint")
