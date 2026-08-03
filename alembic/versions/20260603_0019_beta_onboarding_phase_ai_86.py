"""User onboarding manual steps JSON (AI.86).

Revision ID: 20260603_0019
Revises: 20260603_0018
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0019"
down_revision: Union[str, None] = "20260603_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_manual_completed", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_manual_completed")
