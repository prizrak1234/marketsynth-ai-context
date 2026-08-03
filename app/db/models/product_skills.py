"""DB models for Product Skill Runtime."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin


class ProductSkillInstallationTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "product_skill_installations"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "skill_id",
            name="uq_product_skill_install_owner_skill",
        ),
        Index("ix_product_skill_install_owner", "owner_id"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    skill_id: str = Field(max_length=128, nullable=False)
    skill_version: str = Field(max_length=32, nullable=False)
    install_status: str = Field(max_length=64, nullable=False)
    enabled: bool = Field(default=True, nullable=False)
    checksum_sha256: str | None = Field(default=None, max_length=64)
    configured: bool = Field(default=False, nullable=False)
    last_error: str | None = Field(default=None)
    provenance: str | None = Field(default=None, max_length=240)


class ProductSkillRunTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "product_skill_runs"
    __table_args__ = (
        Index("ix_product_skill_runs_owner_project", "owner_id", "project_id"),
        Index("ix_product_skill_runs_skill", "skill_id"),
        Index(
            "ix_product_skill_runs_idempotency",
            "owner_id",
            "project_id",
            "idempotency_key",
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    skill_id: str = Field(max_length=128, nullable=False)
    skill_version: str = Field(max_length=32, nullable=False)
    status: str = Field(max_length=32, nullable=False)
    selection_mode: str = Field(max_length=32, nullable=False)
    selection_reason: str = Field(max_length=240, nullable=False)
    input_type: str = Field(max_length=64, nullable=False)
    input_ref: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    result_ref: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    evidence: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    safe_error: str | None = Field(default=None)
    error_code: str | None = Field(default=None, max_length=64)
    idempotency_key: str | None = Field(default=None, max_length=128)
    correlation_id: str | None = Field(default=None, max_length=128)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)
