"""Internal BIV E2E deterministic fixture table (RUNTIME-01F)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0064"
down_revision: Union[str, None] = "20260728_0063"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "biv_e2e_deterministic_fixtures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("e2e_run_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id"),
    )
    op.create_index(
        "ix_biv_e2e_deterministic_fixtures_owner",
        "biv_e2e_deterministic_fixtures",
        ["owner_id"],
        unique=True,
    )
    op.create_index(
        "ix_biv_e2e_deterministic_fixtures_run",
        "biv_e2e_deterministic_fixtures",
        ["e2e_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_biv_e2e_deterministic_fixtures_run", table_name="biv_e2e_deterministic_fixtures")
    op.drop_index("ix_biv_e2e_deterministic_fixtures_owner", table_name="biv_e2e_deterministic_fixtures")
    op.drop_table("biv_e2e_deterministic_fixtures")
