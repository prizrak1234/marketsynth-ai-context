"""Append-only Source + InvestigationSourceLink (Commercial MVP P0.3).

Revision ID: 20260614_0031
Revises: 20260614_0030
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260614_0031"
down_revision: Union[str, None] = "20260614_0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("provenance_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("origin", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("publisher", sa.String(length=500), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("country", sa.String(length=64), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=True),
        sa.Column("accessed_at", sa.DateTime(), nullable=True),
        sa.Column("freshness_status", sa.String(length=32), nullable=False),
        sa.Column("reliability_level", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("supersedes_source_id", sa.Uuid(), nullable=True),
        sa.Column("license_type", sa.String(length=128), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("reusable_within_project", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["supersedes_source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sources_owner_id", "sources", ["owner_id"])
    op.create_index("ix_sources_project_id", "sources", ["project_id"])
    op.create_index("ix_sources_source_type", "sources", ["source_type"])
    op.create_index("ix_sources_fingerprint", "sources", ["fingerprint"])
    op.create_index(
        "ix_sources_project_id_fingerprint",
        "sources",
        ["project_id", "fingerprint"],
    )
    op.create_index(
        "ix_sources_supersedes_source_id",
        "sources",
        ["supersedes_source_id"],
    )
    op.create_index("ix_sources_freshness_status", "sources", ["freshness_status"])
    op.create_index("ix_sources_reliability_level", "sources", ["reliability_level"])
    op.create_index("ix_sources_status", "sources", ["status"])
    op.create_index("ix_sources_created_at", "sources", ["created_at"])

    op.create_table(
        "investigation_source_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("investigation_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=500), nullable=True),
        sa.Column("investigation_area", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("added_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "investigation_id",
            "source_id",
            name="uq_investigation_source_links_inv_source",
        ),
    )
    op.create_index(
        "ix_investigation_source_links_owner_id",
        "investigation_source_links",
        ["owner_id"],
    )
    op.create_index(
        "ix_investigation_source_links_project_id",
        "investigation_source_links",
        ["project_id"],
    )
    op.create_index(
        "ix_investigation_source_links_investigation_id",
        "investigation_source_links",
        ["investigation_id"],
    )
    op.create_index(
        "ix_investigation_source_links_source_id",
        "investigation_source_links",
        ["source_id"],
    )
    op.create_index(
        "ix_investigation_source_links_status",
        "investigation_source_links",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_investigation_source_links_status",
        table_name="investigation_source_links",
    )
    op.drop_index(
        "ix_investigation_source_links_source_id",
        table_name="investigation_source_links",
    )
    op.drop_index(
        "ix_investigation_source_links_investigation_id",
        table_name="investigation_source_links",
    )
    op.drop_index(
        "ix_investigation_source_links_project_id",
        table_name="investigation_source_links",
    )
    op.drop_index(
        "ix_investigation_source_links_owner_id",
        table_name="investigation_source_links",
    )
    op.drop_table("investigation_source_links")

    op.drop_index("ix_sources_created_at", table_name="sources")
    op.drop_index("ix_sources_status", table_name="sources")
    op.drop_index("ix_sources_reliability_level", table_name="sources")
    op.drop_index("ix_sources_freshness_status", table_name="sources")
    op.drop_index("ix_sources_supersedes_source_id", table_name="sources")
    op.drop_index("ix_sources_project_id_fingerprint", table_name="sources")
    op.drop_index("ix_sources_fingerprint", table_name="sources")
    op.drop_index("ix_sources_source_type", table_name="sources")
    op.drop_index("ix_sources_project_id", table_name="sources")
    op.drop_index("ix_sources_owner_id", table_name="sources")
    op.drop_table("sources")
