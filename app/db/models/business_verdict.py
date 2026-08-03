"""BusinessVerdict persistence (Commercial MVP P0.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.contracts import (
    BusinessVerdictConfidenceLevel,
    BusinessVerdictEvidenceRole,
    BusinessVerdictLifecycleStatus,
    BusinessVerdictPreparedByType,
    EvidenceAssessmentState,
    EvidenceConfidenceLevel,
    EvidenceMateriality,
    VerdictKind,
    VerdictReadinessStatus,
)


class BusinessVerdictEvidenceSnapshotTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "business_verdict_evidence_snapshots"
    __table_args__ = (
        Index("ix_bv_ev_snap_owner_id", "owner_id"),
        Index("ix_bv_ev_snap_project_id", "project_id"),
        Index("ix_bv_ev_snap_investigation_id", "investigation_id"),
        Index("ix_bv_ev_snap_snapshot_hash", "snapshot_hash"),
        Index("ix_bv_ev_snap_project_investigation_hash", "project_id", "investigation_id", "snapshot_hash"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    investigation_id: UUID = Field(foreign_key="investigations.id", nullable=False)
    snapshot_hash: str = Field(max_length=128, nullable=False)
    evidence_ids: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    evidence_versions: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    accepted_evidence_count: int = Field(default=0, nullable=False)
    missing_critical_count: int = Field(default=0, nullable=False)
    conflicting_critical_count: int = Field(default=0, nullable=False)
    outdated_critical_count: int = Field(default=0, nullable=False)
    area_coverage: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    readiness_status: VerdictReadinessStatus = Field(
        default=VerdictReadinessStatus.NOT_READY,
        nullable=False,
    )
    verdict_readiness_contribution: str = Field(default="partial", max_length=32, nullable=False)


class BusinessVerdictTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "business_verdicts"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_business_verdicts_project_version"),
        Index("ix_business_verdicts_owner_id", "owner_id"),
        Index("ix_business_verdicts_project_id", "project_id"),
        Index("ix_business_verdicts_investigation_id", "investigation_id"),
        Index("ix_business_verdicts_verdict_type", "verdict_type"),
        Index("ix_business_verdicts_lifecycle_status", "lifecycle_status"),
        Index("ix_business_verdicts_version", "version"),
        Index("ix_business_verdicts_evidence_snapshot_hash", "evidence_snapshot_hash"),
        Index("ix_business_verdicts_supersedes_verdict_id", "supersedes_verdict_id"),
        Index("ix_business_verdicts_project_id_version", "project_id", "version"),
        Index("ix_business_verdicts_project_id_lifecycle_status", "project_id", "lifecycle_status"),
        Index("ix_business_verdicts_approved_at", "approved_at"),
        Index("ix_business_verdicts_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    investigation_id: UUID = Field(foreign_key="investigations.id", nullable=False)
    investigation_version: int = Field(nullable=False)
    project_brief_id: UUID = Field(foreign_key="project_briefs.id", nullable=False)
    project_brief_version: int = Field(nullable=False)
    version: int = Field(nullable=False)
    verdict_type: VerdictKind = Field(nullable=False)
    lifecycle_status: BusinessVerdictLifecycleStatus = Field(
        default=BusinessVerdictLifecycleStatus.DRAFT,
        nullable=False,
    )
    confidence_level: BusinessVerdictConfidenceLevel = Field(
        default=BusinessVerdictConfidenceLevel.UNKNOWN,
        nullable=False,
    )
    evidence_snapshot_id: UUID = Field(
        foreign_key="business_verdict_evidence_snapshots.id",
        nullable=False,
    )
    evidence_snapshot_hash: str = Field(max_length=128, nullable=False)
    executive_conclusion: str = Field(max_length=2000, nullable=False)
    executive_rationale: str = Field(max_length=8000, nullable=False)
    primary_business_implication: str = Field(max_length=2000, nullable=False)
    recommended_next_action: str = Field(max_length=2000, nullable=False)
    supporting_evidence_summary: str | None = Field(default=None, max_length=4000, nullable=True)
    counter_evidence_summary: str | None = Field(default=None, max_length=4000, nullable=True)
    conditions: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    critical_risks: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    assumptions: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    change_triggers: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    findings: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    readiness_snapshot: VerdictReadinessStatus = Field(nullable=False)
    prepared_by_type: BusinessVerdictPreparedByType = Field(
        default=BusinessVerdictPreparedByType.USER,
        nullable=False,
    )
    prepared_by_reference: str | None = Field(default=None, max_length=240, nullable=True)
    submitted_by: UUID | None = Field(default=None, foreign_key="users.id", nullable=True)
    submitted_at: datetime | None = Field(default=None, nullable=True)
    approved_by: UUID | None = Field(default=None, foreign_key="users.id", nullable=True)
    approved_at: datetime | None = Field(default=None, nullable=True)
    rejection_reason: str | None = Field(default=None, max_length=2000, nullable=True)
    supersedes_verdict_id: UUID | None = Field(
        default=None,
        foreign_key="business_verdicts.id",
        nullable=True,
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )


class BusinessVerdictEvidenceLinkTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "business_verdict_evidence_links"
    __table_args__ = (
        Index("ix_bv_ev_link_owner_id", "owner_id"),
        Index("ix_bv_ev_link_project_id", "project_id"),
        Index("ix_bv_ev_link_verdict_id", "verdict_id"),
        Index("ix_bv_ev_link_evidence_id", "evidence_id"),
        Index("ix_bv_ev_link_role", "role"),
        UniqueConstraint(
            "verdict_id",
            "evidence_id",
            "role",
            name="uq_bv_ev_link_verdict_evidence_role",
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    verdict_id: UUID = Field(foreign_key="business_verdicts.id", nullable=False)
    evidence_id: UUID = Field(foreign_key="investigation_evidence.id", nullable=False)
    evidence_version: int = Field(nullable=False)
    role: BusinessVerdictEvidenceRole = Field(nullable=False)
    decision_criterion: str | None = Field(default=None, max_length=240, nullable=True)
    materiality_at_snapshot: EvidenceMateriality = Field(nullable=False)
    assessment_state_at_snapshot: EvidenceAssessmentState = Field(nullable=False)
    confidence_at_snapshot: EvidenceConfidenceLevel = Field(nullable=False)
    note: str | None = Field(default=None, max_length=2000, nullable=True)
