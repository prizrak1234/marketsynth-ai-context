"""Content asset revision links (Phase 4.5).

Revision ID: 20260529_0013
Revises: 20260529_0012
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0013"
down_revision: Union[str, None] = "20260529_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _content_asset_columns() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns("content_assets")}


def _content_asset_indexes() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes("content_assets")}


def upgrade() -> None:
    columns = _content_asset_columns()
    indexes = _content_asset_indexes()

    with op.batch_alter_table("content_assets", schema=None) as batch_op:
        if "source_asset_id" not in columns:
            batch_op.add_column(sa.Column("source_asset_id", sa.Uuid(), nullable=True))
        if "source_version_number" not in columns:
            batch_op.add_column(sa.Column("source_version_number", sa.Integer(), nullable=True))
        if "revision_number" not in columns:
            batch_op.add_column(sa.Column("revision_number", sa.Integer(), nullable=True))
        if "ix_content_assets_source_asset_id" not in indexes:
            batch_op.create_index(
                "ix_content_assets_source_asset_id",
                ["source_asset_id"],
            )
        if "ix_content_assets_source_asset_revision" not in indexes:
            batch_op.create_index(
                "ix_content_assets_source_asset_revision",
                ["source_asset_id", "revision_number"],
            )


def downgrade() -> None:
    indexes = _content_asset_indexes()
    columns = _content_asset_columns()

    with op.batch_alter_table("content_assets", schema=None) as batch_op:
        if "ix_content_assets_source_asset_revision" in indexes:
            batch_op.drop_index("ix_content_assets_source_asset_revision")
        if "ix_content_assets_source_asset_id" in indexes:
            batch_op.drop_index("ix_content_assets_source_asset_id")
        if "revision_number" in columns:
            batch_op.drop_column("revision_number")
        if "source_version_number" in columns:
            batch_op.drop_column("source_version_number")
        if "source_asset_id" in columns:
            batch_op.drop_column("source_asset_id")
