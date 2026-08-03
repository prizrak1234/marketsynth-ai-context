"""Persisted commercial upstream snapshots (PRODUCT-01)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import UpstreamSourceMode


class CommercialUpstreamSnapshotTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "commercial_upstream_snapshots"
    __table_args__ = (
        Index("ix_upstream_owner_launch", "owner_id", "launch_pack_request_id"),
        Index("ix_upstream_type", "launch_pack_request_id", "artifact_type"),
        Index("ix_upstream_source_mode", "source_mode"),
        Index("ix_upstream_created_at", "created_at"),
        UniqueConstraint(
            "launch_pack_request_id",
            "artifact_type",
            name="uq_upstream_launch_artifact_type",
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    tenant_id: UUID = Field(nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    launch_pack_request_id: UUID = Field(foreign_key="launch_pack_requests.id", nullable=False)
    artifact_type: str = Field(max_length=64, nullable=False)
    source_skill_id: str = Field(max_length=128, nullable=False)
    source_skill_version: str = Field(max_length=32, nullable=False)
    source_package_hash: str = Field(max_length=64, nullable=False, default="")
    source_output_hash: str = Field(max_length=64, nullable=False)
    source_mode: UpstreamSourceMode = Field(
        default=UpstreamSourceMode.BRIDGED_BIV_SNAPSHOT,
        max_length=32,
        nullable=False,
    )
    bridge_version: str | None = Field(default=None, max_length=64, nullable=True)
    source_biv_id: UUID | None = Field(default=None, nullable=True)
    source_biv_hash: str | None = Field(default=None, max_length=64, nullable=True)
    generated_from_fields: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    limitations: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    replacement_required: bool = Field(default=True, nullable=False)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
