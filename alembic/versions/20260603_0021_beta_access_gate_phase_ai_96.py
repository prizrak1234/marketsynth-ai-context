"""Beta access gate on users (AI.96).

Revision ID: 20260603_0021
Revises: 20260603_0020
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0021"
down_revision: Union[str, None] = "20260603_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("beta_access_status", sa.String(length=16), nullable=False, server_default="pending"),
    )
    op.add_column(
        "users",
        sa.Column("beta_notes", sa.String(length=1024), nullable=True),
    )
    op.create_index("ix_users_beta_access_status", "users", ["beta_access_status"])


def downgrade() -> None:
    op.drop_index("ix_users_beta_access_status", table_name="users")
    op.drop_column("users", "beta_notes")
    op.drop_column("users", "beta_access_status")
