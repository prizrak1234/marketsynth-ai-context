"""Content asset marketing provenance (Phase AI.41).

Revision ID: 20260603_0012
Revises: 20260603_0011
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0012"
down_revision: Union[str, None] = "20260603_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "content_assets",
        sa.Column("source_marketing_plan_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "content_assets",
        sa.Column("source_execution_run_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "content_assets",
        sa.Column("source_specialist_output_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "content_assets",
        sa.Column("source_specialist_type", sa.String(length=32), nullable=True),
    )
    op.create_foreign_key(
        "fk_content_assets_source_marketing_plan_id",
        "content_assets",
        "marketing_plans",
        ["source_marketing_plan_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_content_assets_source_execution_run_id",
        "content_assets",
        "marketing_plan_execution_runs",
        ["source_execution_run_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_content_assets_source_specialist_output_id",
        "content_assets",
        "marketing_specialist_outputs",
        ["source_specialist_output_id"],
        ["id"],
    )
    op.create_index(
        "ix_content_assets_source_marketing_plan_id",
        "content_assets",
        ["source_marketing_plan_id"],
    )
    op.create_index(
        "ix_content_assets_source_execution_run_id",
        "content_assets",
        ["source_execution_run_id"],
    )
    op.create_index(
        "ix_content_assets_source_specialist_output_id",
        "content_assets",
        ["source_specialist_output_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_content_assets_source_specialist_output_id", "content_assets")
    op.drop_index("ix_content_assets_source_execution_run_id", "content_assets")
    op.drop_index("ix_content_assets_source_marketing_plan_id", "content_assets")
    op.drop_constraint(
        "fk_content_assets_source_specialist_output_id",
        "content_assets",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_content_assets_source_execution_run_id",
        "content_assets",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_content_assets_source_marketing_plan_id",
        "content_assets",
        type_="foreignkey",
    )
    op.drop_column("content_assets", "source_specialist_type")
    op.drop_column("content_assets", "source_specialist_output_id")
    op.drop_column("content_assets", "source_execution_run_id")
    op.drop_column("content_assets", "source_marketing_plan_id")
