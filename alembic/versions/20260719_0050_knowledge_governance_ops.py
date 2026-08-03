"""KG.2 — Operational Knowledge Governance tables.

Revision ID: 20260719_0050
Revises: 20260719_0049
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260719_0050"
down_revision: Union[str, None] = "20260719_0049"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kg_objects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_owner_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("foundation_item_id", sa.Uuid(), nullable=True),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["foundation_item_id"], ["knowledge_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_owner_id", "code", name="uq_kg_objects_tenant_code"),
    )
    op.create_index("ix_kg_objects_tenant_owner_id", "kg_objects", ["tenant_owner_id"])
    op.create_index("ix_kg_objects_domain", "kg_objects", ["domain"])
    op.create_index("ix_kg_objects_status", "kg_objects", ["status"])

    op.create_table(
        "kg_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_owner_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("source_uri", sa.String(length=1000), nullable=False),
        sa.Column("source_hash", sa.String(length=128), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.String(length=32), nullable=False),
        sa.Column("freshness", sa.String(length=32), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=True),
        sa.Column("review_date", sa.DateTime(), nullable=True),
        sa.Column("next_review_at", sa.DateTime(), nullable=True),
        sa.Column("effective_from", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.Column("replacement_version_id", sa.Uuid(), nullable=True),
        sa.Column("citation_required", sa.Boolean(), nullable=False),
        sa.Column("lock_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("evidence_chain", sa.JSON(), nullable=False),
        sa.Column("decision_chain", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["object_id"], ["kg_objects.id"]),
        sa.ForeignKeyConstraint(["tenant_owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_id", "version", name="uq_kg_versions_object_version"),
    )
    op.create_index("ix_kg_versions_object_id", "kg_versions", ["object_id"])
    op.create_index("ix_kg_versions_status", "kg_versions", ["status"])
    op.create_index("ix_kg_versions_tenant_owner_id", "kg_versions", ["tenant_owner_id"])

    op.create_table(
        "kg_semantic_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("rule", sa.Text(), nullable=False),
        sa.Column("condition", sa.Text(), nullable=True),
        sa.Column("exception", sa.Text(), nullable=True),
        sa.Column("references_json", sa.JSON(), nullable=False),
        sa.Column("source_location", sa.String(length=500), nullable=True),
        sa.Column("source_hash", sa.String(length=128), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["kg_versions.id"]),
        sa.ForeignKeyConstraint(["object_id"], ["kg_objects.id"]),
        sa.ForeignKeyConstraint(["tenant_owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_semantic_chunks_version_id", "kg_semantic_chunks", ["version_id"])
    op.create_index(
        "ix_kg_semantic_chunks_tenant_owner_id", "kg_semantic_chunks", ["tenant_owner_id"]
    )

    op.create_table(
        "kg_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_owner_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column("rationale", sa.String(length=4000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["kg_versions.id"]),
        sa.ForeignKeyConstraint(["object_id"], ["kg_objects.id"]),
        sa.ForeignKeyConstraint(["tenant_owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_reviews_version_id", "kg_reviews", ["version_id"])

    op.create_table(
        "kg_ownership",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_owner_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["object_id"], ["kg_objects.id"]),
        sa.ForeignKeyConstraint(["tenant_owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_id", name="uq_kg_ownership_object"),
    )
    op.create_index("ix_kg_ownership_owner_user_id", "kg_ownership", ["owner_user_id"])

    op.create_table(
        "kg_benchmark_datasets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("tenant_owner_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_benchmark_datasets_domain", "kg_benchmark_datasets", ["domain"])

    op.create_table(
        "kg_benchmark_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_source_ids", sa.JSON(), nullable=False),
        sa.Column("expected_key_facts", sa.JSON(), nullable=False),
        sa.Column("forbidden_claims", sa.JSON(), nullable=False),
        sa.Column("requires_expert", sa.Boolean(), nullable=False),
        sa.Column("minimum_confidence", sa.String(length=32), nullable=False),
        sa.Column("acceptable_answer_criteria", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["kg_benchmark_datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_benchmark_cases_dataset_id", "kg_benchmark_cases", ["dataset_id"])

    op.create_table(
        "kg_citation_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_owner_id", sa.Uuid(), nullable=False),
        sa.Column("user_request_id", sa.Uuid(), nullable=True),
        sa.Column("snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("claim_id", sa.String(length=64), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("knowledge_version_id", sa.Uuid(), nullable=True),
        sa.Column("semantic_chunk_id", sa.Uuid(), nullable=True),
        sa.Column("source_id", sa.String(length=500), nullable=True),
        sa.Column("confidence", sa.String(length=32), nullable=False),
        sa.Column("citation_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_request_id"], ["user_requests.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["knowledge_snapshots.id"]),
        sa.ForeignKeyConstraint(["knowledge_version_id"], ["kg_versions.id"]),
        sa.ForeignKeyConstraint(["semantic_chunk_id"], ["kg_semantic_chunks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kg_citation_records_snapshot_id", "kg_citation_records", ["snapshot_id"]
    )
    op.create_index(
        "ix_kg_citation_records_tenant_owner_id",
        "kg_citation_records",
        ["tenant_owner_id"],
    )

    op.create_table(
        "kg_freshness_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_owner_id", sa.Uuid(), nullable=False),
        sa.Column("freshness", sa.String(length=32), nullable=False),
        sa.Column("expired", sa.Boolean(), nullable=False),
        sa.Column("deprecated", sa.Boolean(), nullable=False),
        sa.Column("review_date", sa.DateTime(), nullable=True),
        sa.Column("next_review_at", sa.DateTime(), nullable=True),
        sa.Column("safe_message", sa.String(length=500), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["version_id"], ["kg_versions.id"]),
        sa.ForeignKeyConstraint(["object_id"], ["kg_objects.id"]),
        sa.ForeignKeyConstraint(["tenant_owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_freshness_checks_version_id", "kg_freshness_checks", ["version_id"])
    op.create_index(
        "ix_kg_freshness_checks_freshness", "kg_freshness_checks", ["freshness"]
    )

    op.create_table(
        "kg_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_owner_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=True),
        sa.Column("version_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kg_audit_events_tenant_owner_id", "kg_audit_events", ["tenant_owner_id"]
    )
    op.create_index("ix_kg_audit_events_event_type", "kg_audit_events", ["event_type"])

    # Extend knowledge_snapshots with optional governance summary JSON
    op.add_column(
        "knowledge_snapshots",
        sa.Column("governance_meta", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_snapshots", "governance_meta")
    for table in (
        "kg_audit_events",
        "kg_freshness_checks",
        "kg_citation_records",
        "kg_benchmark_cases",
        "kg_benchmark_datasets",
        "kg_ownership",
        "kg_reviews",
        "kg_semantic_chunks",
        "kg_versions",
        "kg_objects",
    ):
        op.drop_table(table)
