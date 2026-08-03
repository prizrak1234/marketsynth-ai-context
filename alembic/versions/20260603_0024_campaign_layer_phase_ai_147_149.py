"""Scenario wizard campaign provenance column (Phase AI.149).

Revision ID: 20260603_0024
Revises: 20260603_0023
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0024"
down_revision: Union[str, None] = "20260603_0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("goal", sa.String(length=4096), nullable=False),
        sa.Column("scenario_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("campaign_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaigns_owner_id", "campaigns", ["owner_id"])
    op.create_index("ix_campaigns_project_id", "campaigns", ["project_id"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"])
    op.create_index("ix_campaigns_scenario_id", "campaigns", ["scenario_id"])
    op.create_index("ix_campaigns_name", "campaigns", ["name"])
    op.create_index("ix_campaigns_created_at", "campaigns", ["created_at"])

    op.add_column(
        "scenario_wizard_runs",
        sa.Column("source_campaign_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_scenario_wizard_runs_source_campaign_id",
        "scenario_wizard_runs",
        ["source_campaign_id"],
    )
    op.create_foreign_key(
        "fk_scenario_wizard_runs_source_campaign_id",
        "scenario_wizard_runs",
        "campaigns",
        ["source_campaign_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_scenario_wizard_runs_source_campaign_id",
        "scenario_wizard_runs",
        type_="foreignkey",
    )
    op.drop_index("ix_scenario_wizard_runs_source_campaign_id", table_name="scenario_wizard_runs")
    op.drop_column("scenario_wizard_runs", "source_campaign_id")
    op.drop_index("ix_campaigns_created_at", table_name="campaigns")
    op.drop_index("ix_campaigns_name", table_name="campaigns")
    op.drop_index("ix_campaigns_scenario_id", table_name="campaigns")
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_index("ix_campaigns_project_id", table_name="campaigns")
    op.drop_index("ix_campaigns_owner_id", table_name="campaigns")
    op.drop_table("campaigns")
