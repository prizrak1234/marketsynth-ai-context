"""Alembic: durable knowledge_items + knowledge_snapshots + UserRequest skill context.

Revision ID: 20260716_0042
Revises: 20260716_0041
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260716_0042"
down_revision: Union[str, None] = "20260716_0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "knowledge_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("knowledge_type", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_format", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("source_uri", sa.String(length=1000), nullable=False),
        sa.Column("source_hash", sa.String(length=128), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("authority", sa.String(length=32), nullable=False),
        sa.Column("tenant_scope", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.Column("citation_required", sa.Boolean(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("specialist_roles", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("review_rationale", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["supersedes_id"], ["knowledge_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "version", name="uq_knowledge_items_code_version"),
    )
    op.create_index("ix_knowledge_items_code", "knowledge_items", ["code"])
    op.create_index("ix_knowledge_items_status", "knowledge_items", ["status"])
    op.create_index("ix_knowledge_items_domain", "knowledge_items", ["domain"])
    op.create_index("ix_knowledge_items_locale", "knowledge_items", ["locale"])
    op.create_index("ix_knowledge_items_owner_id", "knowledge_items", ["owner_id"])
    op.create_index("ix_knowledge_items_project_id", "knowledge_items", ["project_id"])
    op.create_index("ix_knowledge_items_tenant_scope", "knowledge_items", ["tenant_scope"])

    op.create_table(
        "knowledge_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("skill_code", sa.String(length=128), nullable=False),
        sa.Column("skill_version", sa.String(length=32), nullable=False),
        sa.Column("capability_pack_version", sa.String(length=32), nullable=False),
        sa.Column("retrieval_policy_version", sa.String(length=32), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("item_refs", sa.JSON(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_snapshots_owner_id", "knowledge_snapshots", ["owner_id"])
    op.create_index("ix_knowledge_snapshots_project_id", "knowledge_snapshots", ["project_id"])
    op.create_index(
        "ix_knowledge_snapshots_snapshot_hash",
        "knowledge_snapshots",
        ["snapshot_hash"],
    )
    op.create_index("ix_knowledge_snapshots_skill_code", "knowledge_snapshots", ["skill_code"])

    op.add_column("user_requests", sa.Column("skill_code", sa.String(length=128), nullable=True))
    op.add_column("user_requests", sa.Column("skill_version", sa.String(length=32), nullable=True))
    op.add_column(
        "user_requests",
        sa.Column("capability_pack_code", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "user_requests",
        sa.Column("capability_pack_version", sa.String(length=32), nullable=True),
    )
    op.add_column("user_requests", sa.Column("knowledge_snapshot_id", sa.Uuid(), nullable=True))
    op.add_column(
        "user_requests",
        sa.Column("knowledge_snapshot_hash", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "user_requests",
        sa.Column(
            "execution_readiness",
            sa.String(length=32),
            nullable=False,
            server_default="not_applicable",
        ),
    )
    op.add_column(
        "user_requests",
        sa.Column("missing_inputs", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "user_requests",
        sa.Column("quality_profile_code", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "user_requests",
        sa.Column("skill_inputs", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_foreign_key(
        "fk_user_requests_knowledge_snapshot_id",
        "user_requests",
        "knowledge_snapshots",
        ["knowledge_snapshot_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_user_requests_knowledge_snapshot_id",
        "user_requests",
        type_="foreignkey",
    )
    op.drop_column("user_requests", "skill_inputs")
    op.drop_column("user_requests", "quality_profile_code")
    op.drop_column("user_requests", "missing_inputs")
    op.drop_column("user_requests", "execution_readiness")
    op.drop_column("user_requests", "knowledge_snapshot_hash")
    op.drop_column("user_requests", "knowledge_snapshot_id")
    op.drop_column("user_requests", "capability_pack_version")
    op.drop_column("user_requests", "capability_pack_code")
    op.drop_column("user_requests", "skill_version")
    op.drop_column("user_requests", "skill_code")

    op.drop_index("ix_knowledge_snapshots_skill_code", table_name="knowledge_snapshots")
    op.drop_index("ix_knowledge_snapshots_snapshot_hash", table_name="knowledge_snapshots")
    op.drop_index("ix_knowledge_snapshots_project_id", table_name="knowledge_snapshots")
    op.drop_index("ix_knowledge_snapshots_owner_id", table_name="knowledge_snapshots")
    op.drop_table("knowledge_snapshots")

    op.drop_index("ix_knowledge_items_tenant_scope", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_project_id", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_owner_id", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_locale", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_domain", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_status", table_name="knowledge_items")
    op.drop_index("ix_knowledge_items_code", table_name="knowledge_items")
    op.drop_table("knowledge_items")
