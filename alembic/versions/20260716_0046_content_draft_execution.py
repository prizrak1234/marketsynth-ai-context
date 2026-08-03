"""Alembic: content draft execution columns on user_requests (H2.7 slice 1).

Revision ID: 20260716_0046
Revises: 20260716_0045
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0046"
down_revision: Union[str, None] = "20260716_0045"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_requests",
        sa.Column("content_draft", sa.JSON(), nullable=True),
    )
    op.add_column(
        "user_requests",
        sa.Column("content_draft_lineage", sa.JSON(), nullable=True),
    )
    op.add_column(
        "user_requests",
        sa.Column("content_draft_review_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "user_requests",
        sa.Column("prompt_package_hash", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "user_requests",
        sa.Column("prompt_package_version", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "user_requests",
        sa.Column("execution_provider", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "user_requests",
        sa.Column("execution_model", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_requests", "execution_model")
    op.drop_column("user_requests", "execution_provider")
    op.drop_column("user_requests", "prompt_package_version")
    op.drop_column("user_requests", "prompt_package_hash")
    op.drop_column("user_requests", "content_draft_review_status")
    op.drop_column("user_requests", "content_draft_lineage")
    op.drop_column("user_requests", "content_draft")
