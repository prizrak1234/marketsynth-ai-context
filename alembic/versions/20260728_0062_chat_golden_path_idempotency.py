"""Chat golden path — idempotency columns on user_requests."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.migration_helpers import column_exists, index_exists

revision: str = "20260728_0062"
down_revision: Union[str, None] = "20260724_0061"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    table = "user_requests"
    if not column_exists(table, "client_message_id"):
        op.add_column(table, sa.Column("client_message_id", sa.String(length=128), nullable=True))
    if not column_exists(table, "idempotency_key"):
        op.add_column(table, sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    if not column_exists(table, "conversation_id"):
        op.add_column(table, sa.Column("conversation_id", sa.Uuid(), nullable=True))
    if not column_exists(table, "sequence_number"):
        op.add_column(table, sa.Column("sequence_number", sa.Integer(), nullable=True))
    if not column_exists(table, "assistant_run_id"):
        op.add_column(table, sa.Column("assistant_run_id", sa.Uuid(), nullable=True))
    if not column_exists(table, "routing_decision_id"):
        op.add_column(table, sa.Column("routing_decision_id", sa.Uuid(), nullable=True))
    if not column_exists(table, "chat_route"):
        op.add_column(table, sa.Column("chat_route", sa.String(length=64), nullable=True))

    if not index_exists(table, "ix_user_requests_owner_client_message"):
        op.create_index(
            "ix_user_requests_owner_client_message",
            table,
            ["owner_id", "client_message_id"],
            unique=True,
            postgresql_where=sa.text("client_message_id IS NOT NULL"),
        )
    if not index_exists(table, "ix_user_requests_owner_idempotency"):
        op.create_index(
            "ix_user_requests_owner_idempotency",
            table,
            ["owner_id", "idempotency_key"],
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        )


def downgrade() -> None:
    table = "user_requests"
    if index_exists(table, "ix_user_requests_owner_idempotency"):
        op.drop_index("ix_user_requests_owner_idempotency", table_name=table)
    if index_exists(table, "ix_user_requests_owner_client_message"):
        op.drop_index("ix_user_requests_owner_client_message", table_name=table)
    for col in (
        "chat_route",
        "routing_decision_id",
        "assistant_run_id",
        "sequence_number",
        "conversation_id",
        "idempotency_key",
        "client_message_id",
    ):
        if column_exists("user_requests", col):
            op.drop_column("user_requests", col)
