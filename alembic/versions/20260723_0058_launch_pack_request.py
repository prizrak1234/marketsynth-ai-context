"""Alembic: CWF.1a launch pack request + commercial next-step decision."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260723_0058"
down_revision: Union[str, None] = "20260723_0057"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_next_step_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_request_id", sa.Uuid(), nullable=False),
        sa.Column("business_verdict_id", sa.Uuid(), nullable=False),
        sa.Column("selected_action", sa.String(length=64), nullable=False),
        sa.Column("accepted_conditions", sa.JSON(), nullable=False),
        sa.Column("override_reason", sa.String(length=2000), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.ForeignKeyConstraint(["business_verdict_id"], ["business_verdicts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_cnsd_owner_idempotency",
        ),
    )
    op.create_index(
        "ix_cnsd_owner_project",
        "commercial_next_step_decisions",
        ["owner_id", "project_id"],
    )
    op.create_index(
        "ix_cnsd_verdict",
        "commercial_next_step_decisions",
        ["business_verdict_id"],
    )

    op.create_table(
        "launch_pack_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_request_id", sa.Uuid(), nullable=False),
        sa.Column("business_verdict_id", sa.Uuid(), nullable=False),
        sa.Column("next_step_decision_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("selected_next_step", sa.String(length=64), nullable=False),
        sa.Column("accepted_conditions", sa.JSON(), nullable=False),
        sa.Column("source_verdict_type", sa.String(length=64), nullable=False),
        sa.Column("source_confidence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.ForeignKeyConstraint(["business_verdict_id"], ["business_verdicts.id"]),
        sa.ForeignKeyConstraint(
            ["next_step_decision_id"],
            ["commercial_next_step_decisions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id",
            "business_verdict_id",
            name="uq_lpr_owner_verdict",
        ),
    )
    op.create_index(
        "ix_lpr_owner_project",
        "launch_pack_requests",
        ["owner_id", "project_id"],
    )
    op.create_index(
        "ix_lpr_verdict",
        "launch_pack_requests",
        ["business_verdict_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_lpr_verdict", table_name="launch_pack_requests")
    op.drop_index("ix_lpr_owner_project", table_name="launch_pack_requests")
    op.drop_table("launch_pack_requests")
    op.drop_index("ix_cnsd_verdict", table_name="commercial_next_step_decisions")
    op.drop_index("ix_cnsd_owner_project", table_name="commercial_next_step_decisions")
    op.drop_table("commercial_next_step_decisions")
