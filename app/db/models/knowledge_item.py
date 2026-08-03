"""Durable KnowledgeItem + KnowledgeSnapshot persistence (Phase H2.3–H2.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, Text, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    KnowledgeAuthority,
    KnowledgeContentFormat,
    KnowledgeDomain,
    KnowledgeItemStatus,
    KnowledgeTenantScope,
    KnowledgeType,
)


class KnowledgeItemTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    """One immutable row per (code, version). Approved content is never overwritten."""

    __tablename__ = "knowledge_items"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_knowledge_items_code_version"),
        Index("ix_knowledge_items_code", "code"),
        Index("ix_knowledge_items_status", "status"),
        Index("ix_knowledge_items_domain", "domain"),
        Index("ix_knowledge_items_locale", "locale"),
        Index("ix_knowledge_items_owner_id", "owner_id"),
        Index("ix_knowledge_items_project_id", "project_id"),
        Index("ix_knowledge_items_tenant_scope", "tenant_scope"),
    )

    code: str = Field(max_length=128, nullable=False)
    title: str = Field(max_length=500, nullable=False)
    knowledge_type: KnowledgeType = Field(nullable=False)
    domain: KnowledgeDomain = Field(nullable=False)
    content: str = Field(sa_column=Column(Text, nullable=False))
    content_format: KnowledgeContentFormat = Field(
        default=KnowledgeContentFormat.MARKDOWN,
        nullable=False,
    )
    content_hash: str = Field(max_length=128, nullable=False)
    source_uri: str = Field(max_length=1000, nullable=False)
    source_hash: str | None = Field(default=None, max_length=128)
    version: str = Field(max_length=32, nullable=False)
    status: KnowledgeItemStatus = Field(
        default=KnowledgeItemStatus.CANDIDATE,
        nullable=False,
    )
    authority: KnowledgeAuthority = Field(nullable=False)
    tenant_scope: KnowledgeTenantScope = Field(
        default=KnowledgeTenantScope.GLOBAL,
        nullable=False,
    )
    owner_id: UUID | None = Field(default=None, foreign_key="users.id")
    project_id: UUID | None = Field(default=None, foreign_key="projects.id")
    locale: str = Field(default="en", max_length=16, nullable=False)
    valid_from: datetime = Field(default_factory=utc_now, nullable=False)
    valid_until: datetime | None = Field(default=None)
    supersedes_id: UUID | None = Field(
        default=None,
        foreign_key="knowledge_items.id",
    )
    citation_required: bool = Field(default=False, nullable=False)
    tags: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    specialist_roles: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    review_rationale: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    reviewed_at: datetime | None = Field(default=None)
    reviewed_by: str | None = Field(default=None, max_length=128)


class KnowledgeSnapshotTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    """Immutable retrieval snapshot attached to UserRequest (Phase H2.5)."""

    __tablename__ = "knowledge_snapshots"
    __table_args__ = (
        Index("ix_knowledge_snapshots_owner_id", "owner_id"),
        Index("ix_knowledge_snapshots_project_id", "project_id"),
        Index("ix_knowledge_snapshots_snapshot_hash", "snapshot_hash"),
        Index("ix_knowledge_snapshots_skill_code", "skill_code"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID | None = Field(default=None, foreign_key="projects.id")
    skill_code: str = Field(max_length=128, nullable=False)
    skill_version: str = Field(max_length=32, nullable=False)
    capability_pack_version: str = Field(max_length=32, nullable=False)
    retrieval_policy_version: str = Field(max_length=32, nullable=False)
    locale: str = Field(default="ru", max_length=16, nullable=False)
    item_refs: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    snapshot_hash: str = Field(max_length=128, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    # KG.2 — optional governed snapshot summary (version/chunk ids, freshness, policy)
    governance_meta: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
