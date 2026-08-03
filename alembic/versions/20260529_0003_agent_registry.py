"""Agent registry migration — owner, type, capabilities, archive status."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0003"
down_revision: Union[str, None] = "20260529_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("agents") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("capabilities", sa.JSON(), nullable=False, server_default="[]"),
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
        batch_op.drop_index("ix_agents_slug")
        batch_op.drop_column("slug")

    op.execute(
        """
        UPDATE agents
        SET owner_id = (
            SELECT owner_id FROM projects WHERE projects.id = agents.project_id
        )
        WHERE owner_id IS NULL
        """,
    )
    op.execute(
        """
        UPDATE agents
        SET type = 'orchestrator'
        WHERE type IS NULL
        """,
    )
    op.execute(
        """
        UPDATE agents
        SET updated_at = created_at
        WHERE updated_at IS NULL
        """,
    )
    op.execute(
        """
        UPDATE agents
        SET status = 'archived'
        WHERE status = 'disabled'
        """,
    )

    with op.batch_alter_table("agents") as batch_op:
        batch_op.alter_column("owner_id", nullable=False)
        batch_op.alter_column("type", nullable=False)
        batch_op.alter_column("updated_at", nullable=False)

    op.create_index("ix_agents_owner_id", "agents", ["owner_id"], unique=False)
    op.create_index("ix_agents_type", "agents", ["type"], unique=False)
    op.create_index("ix_agents_status", "agents", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_agents_status", table_name="agents")
    op.drop_index("ix_agents_type", table_name="agents")
    op.drop_index("ix_agents_owner_id", table_name="agents")

    with op.batch_alter_table("agents") as batch_op:
        batch_op.add_column(sa.Column("slug", sa.String(length=128), nullable=True))
        batch_op.drop_column("updated_at")
        batch_op.drop_column("capabilities")
        batch_op.drop_column("description")
        batch_op.drop_column("type")
        batch_op.drop_column("owner_id")

    op.execute("UPDATE agents SET slug = id WHERE slug IS NULL")

    with op.batch_alter_table("agents") as batch_op:
        batch_op.alter_column("slug", nullable=False)
        batch_op.create_index("ix_agents_slug", ["slug"], unique=False)

    op.execute(
        """
        UPDATE agents
        SET status = 'disabled'
        WHERE status = 'archived'
        """,
    )
