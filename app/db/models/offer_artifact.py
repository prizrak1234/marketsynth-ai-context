"""Offer artifact persistence (PRODUCT-01)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import OfferApprovalStatus, OfferArtifactStatus


class OfferArtifactTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "offer_artifacts"
    __table_args__ = (
        Index("ix_offer_owner_project", "owner_id", "project_id"),
        Index("ix_offer_launch_pack", "launch_pack_request_id"),
        Index("ix_offer_status", "approval_status"),
        Index("ix_offer_created_at", "created_at"),
        UniqueConstraint("launch_pack_request_id", name="uq_offer_launch_pack"),
        UniqueConstraint(
            "owner_id",
            "generation_idempotency_key",
            name="uq_offer_owner_idempotency",
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    tenant_id: UUID = Field(nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    launch_pack_request_id: UUID = Field(foreign_key="launch_pack_requests.id", nullable=False)
    business_verdict_id: UUID = Field(foreign_key="business_verdicts.id", nullable=False)
    skill_id: str = Field(max_length=128, nullable=False)
    skill_version: str = Field(max_length=32, nullable=False)
    skill_package_hash: str = Field(max_length=64, nullable=False)
    current_version_id: UUID | None = Field(default=None, nullable=True)
    approval_status: OfferApprovalStatus = Field(max_length=32, nullable=False)
    generation_idempotency_key: str | None = Field(default=None, max_length=128, nullable=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
    approved_at: datetime | None = Field(default=None, nullable=True)


class OfferArtifactVersionTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "offer_artifact_versions"
    __table_args__ = (
        Index("ix_offer_version_artifact", "offer_artifact_id"),
        Index("ix_offer_version_status", "status"),
        Index("ix_offer_version_created_at", "created_at"),
        UniqueConstraint("offer_artifact_id", "version_number", name="uq_offer_version_number"),
    )

    offer_artifact_id: UUID = Field(foreign_key="offer_artifacts.id", nullable=False)
    version_number: int = Field(nullable=False, ge=1)
    status: OfferArtifactStatus = Field(max_length=32, nullable=False)
    input_snapshot_hash: str = Field(max_length=64, nullable=False)
    output_hash: str = Field(max_length=64, nullable=False)
    output_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    offer_title: str = Field(default="", max_length=512)
    offer_summary: str = Field(default="", max_length=4000)
    revision_of_id: UUID | None = Field(default=None, nullable=True)
    lineage_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    blocker_code: str | None = Field(default=None, max_length=128, nullable=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class OfferReviewEventTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "offer_review_events"
    __table_args__ = (
        Index("ix_offer_review_artifact", "offer_artifact_id"),
        Index("ix_offer_review_created_at", "created_at"),
        UniqueConstraint(
            "offer_version_id",
            "decision",
            name="uq_offer_review_version_decision",
        ),
    )

    offer_artifact_id: UUID = Field(foreign_key="offer_artifacts.id", nullable=False)
    offer_version_id: UUID = Field(foreign_key="offer_artifact_versions.id", nullable=False)
    reviewer_id: UUID = Field(foreign_key="users.id", nullable=False)
    decision: str = Field(max_length=32, nullable=False)
    expected_output_hash: str = Field(max_length=64, nullable=False)
    comment: str | None = Field(default=None, max_length=2000, nullable=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
