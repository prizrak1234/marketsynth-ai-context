"""Marketing plan scenario provenance (Phase AI.133).

Revision ID: 20260603_0022
Revises: 20260603_0021
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0022"
down_revision: Union[str, None] = "20260603_0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "marketing_plans",
        sa.Column("source_scenario_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "marketing_plans",
        sa.Column("source_scenario_name", sa.String(length=256), nullable=True),
    )
    op.create_index(
        "ix_marketing_plans_source_scenario_id",
        "marketing_plans",
        ["source_scenario_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_plans_source_scenario_id", table_name="marketing_plans")
    op.drop_column("marketing_plans", "source_scenario_name")
    op.drop_column("marketing_plans", "source_scenario_id")
