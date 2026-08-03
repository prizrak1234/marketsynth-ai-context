"""H2.8D — parent_asset_id for immutable A/B child assets.

Revision ID: 20260718_0048
Revises: 20260717_0047
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260718_0048"
down_revision: Union[str, None] = "20260717_0047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generated_visual_assets",
        sa.Column("parent_asset_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_generated_visual_assets_parent_asset_id",
        "generated_visual_assets",
        ["parent_asset_id"],
    )
    op.create_foreign_key(
        "fk_generated_visual_assets_parent_asset_id",
        "generated_visual_assets",
        "generated_visual_assets",
        ["parent_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_generated_visual_assets_parent_asset_id",
        "generated_visual_assets",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_generated_visual_assets_parent_asset_id",
        table_name="generated_visual_assets",
    )
    op.drop_column("generated_visual_assets", "parent_asset_id")
