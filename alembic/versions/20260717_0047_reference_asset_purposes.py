"""Alembic: asset_purposes on reference_visual_assets (H2.8C).

Revision ID: 20260717_0047
Revises: 20260716_0046
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0047"
down_revision: Union[str, None] = "20260716_0046"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reference_visual_assets",
        sa.Column("asset_purposes", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reference_visual_assets", "asset_purposes")
