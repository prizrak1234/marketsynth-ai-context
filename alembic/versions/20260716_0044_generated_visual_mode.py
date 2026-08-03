"""Alembic: generation_mode + asset_type on generated_visual_assets (H2.6A cutover).

Revision ID: 20260716_0044
Revises: 20260716_0043
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0044"
down_revision: Union[str, None] = "20260716_0043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generated_visual_assets",
        sa.Column(
            "generation_mode",
            sa.String(length=32),
            nullable=False,
            server_default="mock",
        ),
    )
    op.add_column(
        "generated_visual_assets",
        sa.Column(
            "asset_type",
            sa.String(length=64),
            nullable=False,
            server_default="diagnostic_placeholder",
        ),
    )
    op.create_index(
        "ix_generated_visual_assets_generation_mode",
        "generated_visual_assets",
        ["generation_mode"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generated_visual_assets_generation_mode",
        table_name="generated_visual_assets",
    )
    op.drop_column("generated_visual_assets", "asset_type")
    op.drop_column("generated_visual_assets", "generation_mode")
