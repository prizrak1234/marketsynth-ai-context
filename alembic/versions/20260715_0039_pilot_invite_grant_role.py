"""Pilot invite grant_role for first-owner bootstrap.

Revision ID: 20260715_0039
Revises: 20260715_0038
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260715_0039"
down_revision: Union[str, None] = "20260715_0038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pilot_invites",
        sa.Column(
            "grant_role",
            sa.String(length=32),
            nullable=False,
            server_default="member",
        ),
    )


def downgrade() -> None:
    op.drop_column("pilot_invites", "grant_role")
