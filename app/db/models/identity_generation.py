"""H2.8E — Identity Generation persistence (manifest + qualification runs)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    IdentityProviderCapability,
    IdentityQualificationRunStatus,
)


class IdentityReferenceManifestTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "identity_reference_manifests"
    __table_args__ = (
        Index("ix_identity_reference_manifests_owner_id", "owner_id"),
        Index("ix_identity_reference_manifests_reference_set_id", "reference_set_id"),
        Index("ix_identity_reference_manifests_immutable_hash", "immutable_hash"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    reference_set_id: UUID = Field(foreign_key="reference_sets.id", nullable=False)
    reference_set_version: str = Field(max_length=128, nullable=False)
    subject_type: str = Field(max_length=32, nullable=False)
    primary_reference_id: UUID | None = Field(default=None)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    immutable_hash: str = Field(max_length=128, nullable=False)
    selection_policy_version: str = Field(default="h2.8e.1", max_length=32)
    provider_code: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class IdentityQualificationRunTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "identity_qualification_runs"
    __table_args__ = (
        Index("ix_identity_qualification_runs_owner_id", "owner_id"),
        Index("ix_identity_qualification_runs_status", "status"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    status: IdentityQualificationRunStatus = Field(
        default=IdentityQualificationRunStatus.DRAFT,
        max_length=64,
        nullable=False,
    )
    baseline_asset_id: UUID | None = Field(
        default=None, foreign_key="generated_visual_assets.id"
    )
    reference_set_id: UUID = Field(foreign_key="reference_sets.id", nullable=False)
    manifest_id: UUID | None = Field(
        default=None, foreign_key="identity_reference_manifests.id"
    )
    manifest_hash: str | None = Field(default=None, max_length=128)
    provider_code: str = Field(max_length=64, nullable=False)
    prompt_summary: str = Field(default="", max_length=500)
    stage: str = Field(default="validate_preflight", max_length=64)
    variants: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    paid_approval: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    readiness_snapshot: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    capability_status: IdentityProviderCapability = Field(
        default=IdentityProviderCapability.UNKNOWN,
        max_length=64,
        nullable=False,
    )
    owner_review_result: str | None = Field(default=None, max_length=128)
    consistency_assist: str | None = Field(default=None, max_length=64)
    report_summary: str | None = Field(default=None, max_length=2000)
    operator_state: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
