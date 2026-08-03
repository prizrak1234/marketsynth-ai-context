"""Reference visual assets and sets (Phase H2.6A-R)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, Text
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    ReferenceAssetPurpose,
    ReferenceQualityStatus,
    ReferenceSafetyStatus,
    ReferenceSetStatus,
    ReferenceSubjectType,
)


class ReferenceVisualAssetTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "reference_visual_assets"
    __table_args__ = (
        Index("ix_reference_visual_assets_owner_id", "owner_id"),
        Index("ix_reference_visual_assets_user_request_id", "user_request_id"),
        Index("ix_reference_visual_assets_checksum", "checksum"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID | None = Field(default=None, foreign_key="projects.id")
    user_request_id: UUID | None = Field(default=None, foreign_key="user_requests.id")
    original_filename: str = Field(max_length=255, nullable=False)
    mime_type: str = Field(max_length=64, nullable=False)
    width: int | None = Field(default=None)
    height: int | None = Field(default=None)
    byte_size: int = Field(nullable=False)
    checksum: str = Field(max_length=128, nullable=False)
    storage_uri: str | None = Field(default=None, max_length=1000)
    content_path: str | None = Field(default=None, max_length=1000)
    asset_purpose: ReferenceAssetPurpose = Field(
        default=ReferenceAssetPurpose.OTHER,
        max_length=64,
        nullable=False,
    )
    asset_purposes: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=True),
    )
    subject_type: ReferenceSubjectType = Field(
        default=ReferenceSubjectType.MIXED,
        max_length=32,
        nullable=False,
    )
    quality_status: ReferenceQualityStatus = Field(
        default=ReferenceQualityStatus.PENDING,
        max_length=32,
        nullable=False,
    )
    quality_notes: str | None = Field(default=None, max_length=1000)
    safety_status: ReferenceSafetyStatus = Field(
        default=ReferenceSafetyStatus.PENDING,
        max_length=32,
        nullable=False,
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    archived_at: datetime | None = Field(default=None)


class ReferenceSetTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "reference_sets"
    __table_args__ = (
        Index("ix_reference_sets_owner_id", "owner_id"),
        Index("ix_reference_sets_user_request_id", "user_request_id"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID | None = Field(default=None, foreign_key="projects.id")
    user_request_id: UUID | None = Field(default=None, foreign_key="user_requests.id")
    title: str = Field(max_length=255, nullable=False)
    subject_type: ReferenceSubjectType = Field(
        default=ReferenceSubjectType.MIXED,
        max_length=32,
        nullable=False,
    )
    preservation_goal: str = Field(default="maximize_recognizability", max_length=128)
    status: ReferenceSetStatus = Field(
        default=ReferenceSetStatus.DRAFT,
        max_length=32,
        nullable=False,
    )
    reference_asset_ids: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    primary_reference_id: UUID | None = Field(default=None)
    identity_notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    immutable_traits: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    allowed_variations: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    forbidden_changes: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    consent_confirmed: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
