"""CWF.1a — persisted Launch Pack request."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import (
    BusinessIdeaValidationVerdictKind,
    CommercialNextStepAction,
    LaunchPackRequestStatus,
)


class LaunchPackRequestTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "launch_pack_requests"
    __table_args__ = (
        Index("ix_lpr_owner_project", "owner_id", "project_id"),
        Index("ix_lpr_verdict", "business_verdict_id"),
        UniqueConstraint(
            "owner_id",
            "business_verdict_id",
            name="uq_lpr_owner_verdict",
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    tenant_id: UUID = Field(nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    user_request_id: UUID = Field(foreign_key="user_requests.id", nullable=False)
    business_verdict_id: UUID = Field(foreign_key="business_verdicts.id", nullable=False)
    next_step_decision_id: UUID = Field(
        foreign_key="commercial_next_step_decisions.id",
        nullable=False,
    )
    status: LaunchPackRequestStatus = Field(max_length=32, nullable=False)
    selected_next_step: CommercialNextStepAction = Field(max_length=64, nullable=False)
    accepted_conditions: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    source_verdict_type: BusinessIdeaValidationVerdictKind = Field(max_length=64, nullable=False)
    source_confidence: int = Field(default=0, nullable=False)
    offer_workflow_status: str = Field(default="not_started", max_length=64, nullable=False)
    offer_artifact_id: UUID | None = Field(default=None, nullable=True)
    blocker_codes: list[Any] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    generation_idempotency_key: str | None = Field(default=None, max_length=128, nullable=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
