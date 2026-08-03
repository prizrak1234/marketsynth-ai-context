"""Alembic: Product Skill Runtime tables (PROGRAM-CONTENT-01-SKILL-RUNTIME-01)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0067"
down_revision: Union[str, None] = "20260802_0066"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_skill_installations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("skill_version", sa.String(length=32), nullable=False),
        sa.Column("install_status", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("configured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("provenance", sa.String(length=240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "skill_id", name="uq_product_skill_install_owner_skill"),
    )
    op.create_index(
        "ix_product_skill_install_owner",
        "product_skill_installations",
        ["owner_id"],
    )

    op.create_table(
        "product_skill_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("skill_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("selection_mode", sa.String(length=32), nullable=False),
        sa.Column("selection_reason", sa.String(length=240), nullable=False),
        sa.Column("input_type", sa.String(length=64), nullable=False),
        sa.Column("input_ref", sa.JSON(), nullable=False),
        sa.Column("result_ref", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("safe_error", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_skill_runs_owner_project",
        "product_skill_runs",
        ["owner_id", "project_id"],
    )
    op.create_index("ix_product_skill_runs_skill", "product_skill_runs", ["skill_id"])
    op.create_index(
        "ix_product_skill_runs_idempotency",
        "product_skill_runs",
        ["owner_id", "project_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_product_skill_runs_idempotency", table_name="product_skill_runs")
    op.drop_index("ix_product_skill_runs_skill", table_name="product_skill_runs")
    op.drop_index("ix_product_skill_runs_owner_project", table_name="product_skill_runs")
    op.drop_table("product_skill_runs")
    op.drop_index("ix_product_skill_install_owner", table_name="product_skill_installations")
    op.drop_table("product_skill_installations")
