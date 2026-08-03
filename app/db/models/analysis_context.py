"""PRODUCT-01.3A — confirmed analysis context for BIV intake gate."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    AnalysisContextDataSourceLabel,
    AnalysisContextSourceMode,
    AnalysisContextState,
)


class AnalysisContextTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "analysis_contexts"
    __table_args__ = (
        Index("ix_analysis_context_owner_project", "owner_id", "project_id"),
        Index("ix_analysis_context_project_active", "project_id", "is_active"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    tenant_id: UUID = Field(nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    state: AnalysisContextState = Field(max_length=32, nullable=False)
    source_mode: AnalysisContextSourceMode | None = Field(default=None, max_length=32)
    data_source_label: AnalysisContextDataSourceLabel | None = Field(default=None, max_length=32)
    idea_description: str = Field(default="", max_length=8000)
    product_or_service: str | None = Field(default=None, max_length=2000)
    target_customer: str | None = Field(default=None, max_length=2000)
    geography: str | None = Field(default=None, max_length=500)
    business_model: str | None = Field(default=None, max_length=1000)
    pricing_or_revenue_model: str | None = Field(default=None, max_length=1000)
    current_stage: str | None = Field(default=None, max_length=500)
    budget_context: str | None = Field(default=None, max_length=500)
    known_competitors: str | None = Field(default=None, max_length=2000)
    analysis_goal: str | None = Field(default=None, max_length=1000)
    target_customer_unknown: bool = Field(default=False, nullable=False)
    geography_unknown: bool = Field(default=False, nullable=False)
    confirmed_by_user: bool = Field(default=False, nullable=False)
    confirmed_at: datetime | None = Field(default=None)
    input_snapshot_hash: str | None = Field(default=None, max_length=64)
    source_snapshot_id: UUID | None = Field(default=None, foreign_key="analysis_contexts.id")
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
