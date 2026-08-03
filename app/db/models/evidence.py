"""Investigation Evidence persistence (Commercial MVP P0.4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import (
    EvidenceAssessmentState,
    EvidenceConfidenceLevel,
    EvidenceInvestigationArea,
    EvidenceLifecycleStatus,
    EvidenceLocatorType,
    EvidenceMateriality,
    EvidencePreparedByType,
    EvidenceSourceStance,
    EvidenceType,
)


class InvestigationEvidenceTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "investigation_evidence"
    __table_args__ = (
        Index("ix_investigation_evidence_owner_id", "owner_id"),
        Index("ix_investigation_evidence_project_id", "project_id"),
        Index("ix_investigation_evidence_investigation_id", "investigation_id"),
        Index("ix_investigation_evidence_lifecycle_status", "lifecycle_status"),
        Index("ix_investigation_evidence_assessment_state", "assessment_state"),
        Index("ix_investigation_evidence_confidence_level", "confidence_level"),
        Index("ix_investigation_evidence_materiality", "materiality"),
        Index("ix_investigation_evidence_evidence_type", "evidence_type"),
        Index("ix_investigation_evidence_investigation_area", "investigation_area"),
        Index("ix_investigation_evidence_input_fingerprint", "input_fingerprint"),
        Index("ix_investigation_evidence_supersedes_evidence_id", "supersedes_evidence_id"),
        Index("ix_investigation_evidence_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    investigation_id: UUID = Field(foreign_key="investigations.id", nullable=False)
    claim: str = Field(max_length=2000, nullable=False)
    evidence_type: EvidenceType = Field(nullable=False)
    investigation_area: EvidenceInvestigationArea = Field(
        default=EvidenceInvestigationArea.OTHER,
        nullable=False,
    )
    lifecycle_status: EvidenceLifecycleStatus = Field(
        default=EvidenceLifecycleStatus.DRAFT,
        nullable=False,
    )
    assessment_state: EvidenceAssessmentState = Field(
        default=EvidenceAssessmentState.UNVERIFIED,
        nullable=False,
    )
    confidence_level: EvidenceConfidenceLevel = Field(
        default=EvidenceConfidenceLevel.UNKNOWN,
        nullable=False,
    )
    materiality: EvidenceMateriality = Field(
        default=EvidenceMateriality.MEDIUM,
        nullable=False,
    )
    review_note: str | None = Field(default=None, max_length=2000, nullable=True)
    why_it_matters: str | None = Field(default=None, max_length=2000, nullable=True)
    recommended_source_type: str | None = Field(default=None, max_length=64, nullable=True)
    prepared_by_type: EvidencePreparedByType = Field(
        default=EvidencePreparedByType.USER,
        nullable=False,
    )
    prepared_by_reference: str | None = Field(default=None, max_length=128, nullable=True)
    version: int = Field(default=1, nullable=False)
    input_fingerprint: str = Field(max_length=128, nullable=False)
    supersedes_evidence_id: UUID | None = Field(
        default=None,
        foreign_key="investigation_evidence.id",
        nullable=True,
    )
    reviewed_by: UUID | None = Field(default=None, foreign_key="users.id", nullable=True)
    reviewed_at: datetime | None = Field(default=None, nullable=True)
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )


class EvidenceSourceLinkTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "evidence_source_links"
    __table_args__ = (
        UniqueConstraint(
            "evidence_id",
            "source_id",
            "stance",
            name="uq_evidence_source_links_evidence_source_stance",
        ),
        Index("ix_evidence_source_links_owner_id", "owner_id"),
        Index("ix_evidence_source_links_project_id", "project_id"),
        Index("ix_evidence_source_links_investigation_id", "investigation_id"),
        Index("ix_evidence_source_links_evidence_id", "evidence_id"),
        Index("ix_evidence_source_links_source_id", "source_id"),
        Index("ix_evidence_source_links_stance", "stance"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    investigation_id: UUID = Field(foreign_key="investigations.id", nullable=False)
    evidence_id: UUID = Field(foreign_key="investigation_evidence.id", nullable=False)
    source_id: UUID = Field(foreign_key="sources.id", nullable=False)
    stance: EvidenceSourceStance = Field(nullable=False)
    locator_type: EvidenceLocatorType = Field(
        default=EvidenceLocatorType.UNKNOWN,
        nullable=False,
    )
    locator_value: str | None = Field(default=None, max_length=500, nullable=True)
    excerpt: str | None = Field(default=None, max_length=2000, nullable=True)
    excerpt_hash: str | None = Field(default=None, max_length=128, nullable=True)
    note: str | None = Field(default=None, max_length=2000, nullable=True)
    added_by: UUID = Field(foreign_key="users.id", nullable=False)
