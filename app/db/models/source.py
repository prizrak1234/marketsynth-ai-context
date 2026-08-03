"""Source and InvestigationSourceLink persistence (Commercial MVP P0.3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import (
    InvestigationSourceLinkStatus,
    SourceFreshnessStatus,
    SourceProvenanceType,
    SourceReliabilityLevel,
    SourceStatus,
    SourceType,
)


class SourceTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "sources"
    __table_args__ = (
        Index("ix_sources_owner_id", "owner_id"),
        Index("ix_sources_project_id", "project_id"),
        Index("ix_sources_source_type", "source_type"),
        Index("ix_sources_fingerprint", "fingerprint"),
        Index("ix_sources_project_id_fingerprint", "project_id", "fingerprint"),
        Index("ix_sources_supersedes_source_id", "supersedes_source_id"),
        Index("ix_sources_freshness_status", "freshness_status"),
        Index("ix_sources_reliability_level", "reliability_level"),
        Index("ix_sources_status", "status"),
        Index("ix_sources_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    source_type: SourceType = Field(nullable=False)
    provenance_type: SourceProvenanceType = Field(
        default=SourceProvenanceType.UNKNOWN,
        nullable=False,
    )
    title: str = Field(max_length=500, nullable=False)
    origin: str = Field(default="", max_length=500, nullable=False)
    url: str | None = Field(default=None, max_length=2000, nullable=True)
    domain: str | None = Field(default=None, max_length=255, nullable=True)
    publisher: str | None = Field(default=None, max_length=500, nullable=True)
    language: str | None = Field(default=None, max_length=32, nullable=True)
    country: str | None = Field(default=None, max_length=64, nullable=True)
    published_at: datetime | None = Field(default=None, nullable=True)
    captured_at: datetime | None = Field(default=None, nullable=True)
    accessed_at: datetime | None = Field(default=None, nullable=True)
    freshness_status: SourceFreshnessStatus = Field(
        default=SourceFreshnessStatus.UNKNOWN,
        nullable=False,
    )
    reliability_level: SourceReliabilityLevel = Field(
        default=SourceReliabilityLevel.UNVERIFIED,
        nullable=False,
    )
    status: SourceStatus = Field(default=SourceStatus.REGISTERED, nullable=False)
    fingerprint: str = Field(max_length=128, nullable=False)
    content_hash: str | None = Field(default=None, max_length=128, nullable=True)
    etag: str | None = Field(default=None, max_length=255, nullable=True)
    version: int = Field(nullable=False, default=1)
    supersedes_source_id: UUID | None = Field(
        default=None,
        foreign_key="sources.id",
        nullable=True,
    )
    license_type: str | None = Field(default=None, max_length=128, nullable=True)
    capabilities: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    reusable_within_project: bool = Field(default=True, nullable=False)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )


class InvestigationSourceLinkTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "investigation_source_links"
    __table_args__ = (
        UniqueConstraint(
            "investigation_id",
            "source_id",
            name="uq_investigation_source_links_inv_source",
        ),
        Index("ix_investigation_source_links_owner_id", "owner_id"),
        Index("ix_investigation_source_links_project_id", "project_id"),
        Index("ix_investigation_source_links_investigation_id", "investigation_id"),
        Index("ix_investigation_source_links_source_id", "source_id"),
        Index("ix_investigation_source_links_status", "status"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    investigation_id: UUID = Field(foreign_key="investigations.id", nullable=False)
    source_id: UUID = Field(foreign_key="sources.id", nullable=False)
    purpose: str | None = Field(default=None, max_length=500, nullable=True)
    investigation_area: str | None = Field(default=None, max_length=64, nullable=True)
    notes: str | None = Field(default=None, max_length=2000, nullable=True)
    status: InvestigationSourceLinkStatus = Field(
        default=InvestigationSourceLinkStatus.ACCEPTED,
        nullable=False,
    )
    added_by: UUID = Field(foreign_key="users.id", nullable=False)
