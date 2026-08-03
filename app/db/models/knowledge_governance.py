"""KG.2 — Operational Knowledge Governance persistence.

Lineage: object → version → chunks → review → publication.
Versions are immutable. Soft archive only.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, Text, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    KnowledgeConfidenceLevel,
    KnowledgeDomain,
    KnowledgeFreshnessState,
    KnowledgeGovernanceStatus,
    KnowledgeVisibility,
)


class KnowledgeObjectTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    """Stable identity across versions (governance axis)."""

    __tablename__ = "kg_objects"
    __table_args__ = (
        Index("ix_kg_objects_tenant_owner_id", "tenant_owner_id"),
        Index("ix_kg_objects_domain", "domain"),
        Index("ix_kg_objects_status", "status"),
        UniqueConstraint("tenant_owner_id", "code", name="uq_kg_objects_tenant_code"),
    )

    tenant_owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    code: str = Field(max_length=128, nullable=False)
    title: str = Field(max_length=500, nullable=False)
    domain: KnowledgeDomain = Field(nullable=False)
    visibility: KnowledgeVisibility = Field(
        default=KnowledgeVisibility.OWNER, nullable=False
    )
    status: KnowledgeGovernanceStatus = Field(
        default=KnowledgeGovernanceStatus.DRAFT, nullable=False
    )
    foundation_item_id: UUID | None = Field(
        default=None, foreign_key="knowledge_items.id"
    )
    current_version_id: UUID | None = Field(default=None)
    archived_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )


class KnowledgeVersionTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    """Immutable knowledge version — never overwrite content."""

    __tablename__ = "kg_versions"
    __table_args__ = (
        UniqueConstraint("object_id", "version", name="uq_kg_versions_object_version"),
        Index("ix_kg_versions_object_id", "object_id"),
        Index("ix_kg_versions_status", "status"),
        Index("ix_kg_versions_tenant_owner_id", "tenant_owner_id"),
    )

    object_id: UUID = Field(foreign_key="kg_objects.id", nullable=False)
    tenant_owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    version: str = Field(max_length=32, nullable=False)
    status: KnowledgeGovernanceStatus = Field(
        default=KnowledgeGovernanceStatus.DRAFT, nullable=False
    )
    content: str = Field(sa_column=Column(Text, nullable=False))
    content_hash: str = Field(max_length=128, nullable=False)
    source_uri: str = Field(max_length=1000, nullable=False)
    source_hash: str | None = Field(default=None, max_length=128)
    language: str = Field(default="ru", max_length=16, nullable=False)
    domain: KnowledgeDomain = Field(nullable=False)
    confidence: KnowledgeConfidenceLevel = Field(
        default=KnowledgeConfidenceLevel.UNVERIFIED, nullable=False
    )
    freshness: KnowledgeFreshnessState = Field(
        default=KnowledgeFreshnessState.UNKNOWN, nullable=False
    )
    owner_user_id: UUID | None = Field(default=None, foreign_key="users.id")
    reviewer_user_id: UUID | None = Field(default=None, foreign_key="users.id")
    review_date: datetime | None = Field(default=None)
    next_review_at: datetime | None = Field(default=None)
    effective_from: datetime | None = Field(default=None)
    published_at: datetime | None = Field(default=None)
    supersedes_version_id: UUID | None = Field(default=None)
    replacement_version_id: UUID | None = Field(default=None)
    citation_required: bool = Field(default=True, nullable=False)
    lock_version: int = Field(default=1, nullable=False)  # optimistic
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    archived_at: datetime | None = Field(default=None)
    evidence_chain: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    decision_chain: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )


class SemanticChunkTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "kg_semantic_chunks"
    __table_args__ = (
        Index("ix_kg_semantic_chunks_version_id", "version_id"),
        Index("ix_kg_semantic_chunks_tenant_owner_id", "tenant_owner_id"),
    )

    version_id: UUID = Field(foreign_key="kg_versions.id", nullable=False)
    object_id: UUID = Field(foreign_key="kg_objects.id", nullable=False)
    tenant_owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    title: str = Field(max_length=500, nullable=False)
    intent: str = Field(sa_column=Column(Text, nullable=False))
    rule: str = Field(sa_column=Column(Text, nullable=False))
    condition: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    exception: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    references_json: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    source_location: str | None = Field(default=None, max_length=500)
    source_hash: str | None = Field(default=None, max_length=128)
    language: str = Field(default="ru", max_length=16, nullable=False)
    domain: KnowledgeDomain = Field(nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class KnowledgeReviewTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "kg_reviews"
    __table_args__ = (Index("ix_kg_reviews_version_id", "version_id"),)

    version_id: UUID = Field(foreign_key="kg_versions.id", nullable=False)
    object_id: UUID = Field(foreign_key="kg_objects.id", nullable=False)
    tenant_owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    reviewer_user_id: UUID = Field(foreign_key="users.id", nullable=False)
    decision: str = Field(max_length=64, nullable=False)  # approve|reject|request_changes
    rationale: str | None = Field(default=None, max_length=4000)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class KnowledgeOwnershipTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "kg_ownership"
    __table_args__ = (
        UniqueConstraint("object_id", name="uq_kg_ownership_object"),
        Index("ix_kg_ownership_owner_user_id", "owner_user_id"),
    )

    object_id: UUID = Field(foreign_key="kg_objects.id", nullable=False)
    tenant_owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    owner_user_id: UUID = Field(foreign_key="users.id", nullable=False)
    reviewer_user_id: UUID | None = Field(default=None, foreign_key="users.id")
    assigned_at: datetime = Field(default_factory=utc_now, nullable=False)
    assigned_by: UUID | None = Field(default=None, foreign_key="users.id")


class BenchmarkDatasetTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "kg_benchmark_datasets"
    __table_args__ = (Index("ix_kg_benchmark_datasets_domain", "domain"),)

    name: str = Field(max_length=255, nullable=False)
    version: str = Field(default="1.0", max_length=32, nullable=False)
    domain: str = Field(max_length=64, nullable=False)
    tenant_owner_id: UUID | None = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )


class BenchmarkCaseTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "kg_benchmark_cases"
    __table_args__ = (Index("ix_kg_benchmark_cases_dataset_id", "dataset_id"),)

    dataset_id: UUID = Field(foreign_key="kg_benchmark_datasets.id", nullable=False)
    question: str = Field(sa_column=Column(Text, nullable=False))
    expected_source_ids: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    expected_key_facts: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    forbidden_claims: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    requires_expert: bool = Field(default=False, nullable=False)
    minimum_confidence: str = Field(default="medium", max_length=32)
    acceptable_answer_criteria: list[Any] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class CitationRecordTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "kg_citation_records"
    __table_args__ = (
        Index("ix_kg_citation_records_snapshot_id", "snapshot_id"),
        Index("ix_kg_citation_records_tenant_owner_id", "tenant_owner_id"),
    )

    tenant_owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    user_request_id: UUID | None = Field(default=None, foreign_key="user_requests.id")
    snapshot_id: UUID | None = Field(default=None, foreign_key="knowledge_snapshots.id")
    claim_id: str = Field(max_length=64, nullable=False)
    claim_text: str = Field(sa_column=Column(Text, nullable=False))
    knowledge_version_id: UUID | None = Field(
        default=None, foreign_key="kg_versions.id"
    )
    semantic_chunk_id: UUID | None = Field(
        default=None, foreign_key="kg_semantic_chunks.id"
    )
    source_id: str | None = Field(default=None, max_length=500)
    confidence: str = Field(default="unverified", max_length=32)
    citation_status: str = Field(
        default="present", max_length=32
    )  # present|missing|opinion|blocked
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class KnowledgeFreshnessCheckTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "kg_freshness_checks"
    __table_args__ = (
        Index("ix_kg_freshness_checks_version_id", "version_id"),
        Index("ix_kg_freshness_checks_freshness", "freshness"),
    )

    version_id: UUID = Field(foreign_key="kg_versions.id", nullable=False)
    object_id: UUID = Field(foreign_key="kg_objects.id", nullable=False)
    tenant_owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    freshness: KnowledgeFreshnessState = Field(nullable=False)
    expired: bool = Field(default=False, nullable=False)
    deprecated: bool = Field(default=False, nullable=False)
    review_date: datetime | None = Field(default=None)
    next_review_at: datetime | None = Field(default=None)
    safe_message: str = Field(default="", max_length=500)
    checked_at: datetime = Field(default_factory=utc_now, nullable=False)


class KnowledgeAuditEventTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "kg_audit_events"
    __table_args__ = (
        Index("ix_kg_audit_events_tenant_owner_id", "tenant_owner_id"),
        Index("ix_kg_audit_events_event_type", "event_type"),
    )

    tenant_owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    event_type: str = Field(max_length=64, nullable=False)
    object_id: UUID | None = Field(default=None)
    version_id: UUID | None = Field(default=None)
    actor_user_id: UUID | None = Field(default=None, foreign_key="users.id")
    payload: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
