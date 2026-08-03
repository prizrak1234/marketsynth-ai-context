"""Project JSON config column for execution engine overrides.

Revision ID: 20260529_0010
Revises: 20260529_0009
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0010"
down_revision: Union[str, None] = "20260529_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_column("config")
