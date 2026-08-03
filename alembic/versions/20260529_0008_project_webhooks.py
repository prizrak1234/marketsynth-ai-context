"""Project outbound webhook subscriptions."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0008"
down_revision: Union[str, None] = "20260529_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_webhooks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("signing_secret", sa.String(length=255), nullable=False),
        sa.Column("subscribed_event_types", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_webhooks_owner_id", "project_webhooks", ["owner_id"])
    op.create_index("ix_project_webhooks_project_id", "project_webhooks", ["project_id"])
    op.create_index("ix_project_webhooks_is_active", "project_webhooks", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_project_webhooks_is_active", table_name="project_webhooks")
    op.drop_index("ix_project_webhooks_project_id", table_name="project_webhooks")
    op.drop_index("ix_project_webhooks_owner_id", table_name="project_webhooks")
    op.drop_table("project_webhooks")
