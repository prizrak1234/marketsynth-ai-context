"""Webhook delivery attempt logs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0009"
down_revision: Union[str, None] = "20260529_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_delivery_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("webhook_id", sa.Uuid(), nullable=True),
        sa.Column("event_outbox_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("target_url_preview", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("response_preview", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_outbox_id"], ["event_outbox.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["webhook_id"], ["project_webhooks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_webhook_delivery_logs_owner_id",
        "webhook_delivery_logs",
        ["owner_id"],
    )
    op.create_index(
        "ix_webhook_delivery_logs_project_id",
        "webhook_delivery_logs",
        ["project_id"],
    )
    op.create_index(
        "ix_webhook_delivery_logs_webhook_id",
        "webhook_delivery_logs",
        ["webhook_id"],
    )
    op.create_index(
        "ix_webhook_delivery_logs_event_outbox_id",
        "webhook_delivery_logs",
        ["event_outbox_id"],
    )
    op.create_index(
        "ix_webhook_delivery_logs_status",
        "webhook_delivery_logs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_delivery_logs_status", table_name="webhook_delivery_logs")
    op.drop_index(
        "ix_webhook_delivery_logs_event_outbox_id",
        table_name="webhook_delivery_logs",
    )
    op.drop_index("ix_webhook_delivery_logs_webhook_id", table_name="webhook_delivery_logs")
    op.drop_index("ix_webhook_delivery_logs_project_id", table_name="webhook_delivery_logs")
    op.drop_index("ix_webhook_delivery_logs_owner_id", table_name="webhook_delivery_logs")
    op.drop_table("webhook_delivery_logs")
