"""Content asset versioning (Phase 4.4).

Revision ID: 20260529_0012
Revises: 20260529_0011
"""

from __future__ import annotations

import json
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_0012"
down_revision: Union[str, None] = "20260529_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_asset_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_by_source", sa.String(length=32), nullable=False),
        sa.Column("created_by_agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["content_assets.id"]),
        sa.ForeignKeyConstraint(["created_by_agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "version_number", name="uq_content_asset_versions_asset_version"),
    )
    op.create_index(
        "ix_content_asset_versions_owner_project",
        "content_asset_versions",
        ["owner_id", "project_id"],
    )
    op.create_index(
        "ix_content_asset_versions_asset_id",
        "content_asset_versions",
        ["asset_id"],
    )
    op.create_index(
        "ix_content_asset_versions_created_at",
        "content_asset_versions",
        ["created_at"],
    )

    op.add_column(
        "content_assets",
        sa.Column(
            "current_version_number",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "content_assets",
        sa.Column("approved_version_number", sa.Integer(), nullable=True),
    )

    bind = op.get_bind()
    assets = bind.execute(
        sa.text(
            """
            SELECT id, owner_id, project_id, title, body, metadata,
                   agent_run_id, created_at, status
            FROM content_assets
            """
        ),
    ).mappings().all()
    for asset in assets:
        metadata = asset["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        bind.execute(
            sa.text(
                """
                INSERT INTO content_asset_versions (
                    id, owner_id, project_id, asset_id, version_number,
                    title, body, metadata, created_by_source,
                    created_by_agent_run_id, created_at
                )
                VALUES (
                    :id, :owner_id, :project_id, :asset_id, 1,
                    :title, :body, :metadata, 'system',
                    :agent_run_id, :created_at
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "owner_id": asset["owner_id"],
                "project_id": asset["project_id"],
                "asset_id": asset["id"],
                "title": asset["title"],
                "body": asset["body"] or "",
                "metadata": json.dumps(metadata or {}),
                "agent_run_id": asset["agent_run_id"],
                "created_at": asset["created_at"],
            },
        )
        if asset["status"] == "approved":
            bind.execute(
                sa.text(
                    """
                    UPDATE content_assets
                    SET approved_version_number = 1
                    WHERE id = :asset_id
                    """
                ),
                {"asset_id": asset["id"]},
            )


def downgrade() -> None:
    op.drop_column("content_assets", "approved_version_number")
    op.drop_column("content_assets", "current_version_number")
    op.drop_index("ix_content_asset_versions_created_at", table_name="content_asset_versions")
    op.drop_index("ix_content_asset_versions_asset_id", table_name="content_asset_versions")
    op.drop_index(
        "ix_content_asset_versions_owner_project",
        table_name="content_asset_versions",
    )
    op.drop_table("content_asset_versions")
