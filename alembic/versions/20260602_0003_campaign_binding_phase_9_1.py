"""Campaign binding for assets and publication jobs (Phase 9.1).

Revision ID: 20260602_0003
Revises: 20260602_0002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.migration_helpers import column_exists, index_exists

revision: str = "20260602_0003"
down_revision: Union[str, None] = "20260602_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _bind_content_campaign() -> None:
    if column_exists("content_assets", "campaign_id"):
        if not index_exists("content_assets", "ix_content_assets_campaign_id"):
            op.create_index("ix_content_assets_campaign_id", "content_assets", ["campaign_id"])
        return
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("content_assets") as batch_op:
            batch_op.add_column(sa.Column("campaign_id", sa.Uuid(), nullable=True))
            batch_op.create_foreign_key(
                "fk_content_assets_campaign_id",
                "marketing_campaigns",
                ["campaign_id"],
                ["id"],
            )
            batch_op.create_index("ix_content_assets_campaign_id", ["campaign_id"])
    else:
        op.add_column("content_assets", sa.Column("campaign_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "fk_content_assets_campaign_id",
            "content_assets",
            "marketing_campaigns",
            ["campaign_id"],
            ["id"],
        )
        op.create_index("ix_content_assets_campaign_id", "content_assets", ["campaign_id"])


def _bind_publication_campaign() -> None:
    if column_exists("publication_jobs", "campaign_id"):
        if not index_exists("publication_jobs", "ix_publication_jobs_campaign_id"):
            op.create_index("ix_publication_jobs_campaign_id", "publication_jobs", ["campaign_id"])
        return
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("publication_jobs") as batch_op:
            batch_op.add_column(sa.Column("campaign_id", sa.Uuid(), nullable=True))
            batch_op.create_foreign_key(
                "fk_publication_jobs_campaign_id",
                "marketing_campaigns",
                ["campaign_id"],
                ["id"],
            )
            batch_op.create_index("ix_publication_jobs_campaign_id", ["campaign_id"])
    else:
        op.add_column("publication_jobs", sa.Column("campaign_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "fk_publication_jobs_campaign_id",
            "publication_jobs",
            "marketing_campaigns",
            ["campaign_id"],
            ["id"],
        )
        op.create_index("ix_publication_jobs_campaign_id", "publication_jobs", ["campaign_id"])


def upgrade() -> None:
    _bind_content_campaign()
    _bind_publication_campaign()


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("publication_jobs") as batch_op:
            batch_op.drop_index("ix_publication_jobs_campaign_id")
            batch_op.drop_constraint("fk_publication_jobs_campaign_id", type_="foreignkey")
            batch_op.drop_column("campaign_id")
        with op.batch_alter_table("content_assets") as batch_op:
            batch_op.drop_index("ix_content_assets_campaign_id")
            batch_op.drop_constraint("fk_content_assets_campaign_id", type_="foreignkey")
            batch_op.drop_column("campaign_id")
    else:
        op.drop_index("ix_publication_jobs_campaign_id", table_name="publication_jobs")
        op.drop_constraint("fk_publication_jobs_campaign_id", "publication_jobs", type_="foreignkey")
        op.drop_column("publication_jobs", "campaign_id")

        op.drop_index("ix_content_assets_campaign_id", table_name="content_assets")
        op.drop_constraint("fk_content_assets_campaign_id", "content_assets", type_="foreignkey")
        op.drop_column("content_assets", "campaign_id")
