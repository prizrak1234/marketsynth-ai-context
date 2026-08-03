"""Pilot invites + email_verified_at (invite registration).

Revision ID: 20260715_0038
Revises: 20260715_0037
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260715_0038"
down_revision: Union[str, None] = "20260715_0037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "pilot_invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email_normalized", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("accepted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_pilot_invites_email_normalized", "pilot_invites", ["email_normalized"])
    op.create_index("ix_pilot_invites_token_hash", "pilot_invites", ["token_hash"])
    op.create_index("ix_pilot_invites_status", "pilot_invites", ["status"])
    op.create_index("ix_pilot_invites_expires_at", "pilot_invites", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_pilot_invites_expires_at", table_name="pilot_invites")
    op.drop_index("ix_pilot_invites_status", table_name="pilot_invites")
    op.drop_index("ix_pilot_invites_token_hash", table_name="pilot_invites")
    op.drop_index("ix_pilot_invites_email_normalized", table_name="pilot_invites")
    op.drop_table("pilot_invites")
    op.drop_column("users", "email_verified_at")
