"""Publishing reliability — idempotency, replay, snapshot hash (AI.66–AI.68).

Revision ID: 20260603_0017
Revises: 20260603_0016
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260603_0017"
down_revision: Union[str, None] = "20260603_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "publication_package_jobs",
        sa.Column("snapshot_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "publication_package_jobs",
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "publication_package_jobs",
        sa.Column("idempotency_fingerprint", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "publication_package_jobs",
        sa.Column("replay_of_job_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_publication_package_jobs_replay_of_job_id",
        "publication_package_jobs",
        "publication_package_jobs",
        ["replay_of_job_id"],
        ["id"],
    )
    op.create_index(
        "ix_publication_package_jobs_idempotency_key_hash",
        "publication_package_jobs",
        ["owner_id", "project_id", "idempotency_key_hash"],
    )
    op.create_index(
        "ix_publication_package_jobs_replay_of_job_id",
        "publication_package_jobs",
        ["replay_of_job_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_publication_package_jobs_replay_of_job_id",
        table_name="publication_package_jobs",
    )
    op.drop_index(
        "ix_publication_package_jobs_idempotency_key_hash",
        table_name="publication_package_jobs",
    )
    op.drop_constraint(
        "fk_publication_package_jobs_replay_of_job_id",
        "publication_package_jobs",
        type_="foreignkey",
    )
    op.drop_column("publication_package_jobs", "replay_of_job_id")
    op.drop_column("publication_package_jobs", "idempotency_fingerprint")
    op.drop_column("publication_package_jobs", "idempotency_key_hash")
    op.drop_column("publication_package_jobs", "snapshot_hash")
