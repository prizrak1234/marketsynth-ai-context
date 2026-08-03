"""CWF.1a — persisted commercial next-step decision."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import CommercialNextStepAction


class CommercialNextStepDecisionTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "commercial_next_step_decisions"
    __table_args__ = (
        Index("ix_cnsd_owner_project", "owner_id", "project_id"),
        Index("ix_cnsd_verdict", "business_verdict_id"),
        UniqueConstraint(
            "owner_id",
            "idempotency_key",
            name="uq_cnsd_owner_idempotency",
        ),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    tenant_id: UUID = Field(nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    user_request_id: UUID = Field(foreign_key="user_requests.id", nullable=False)
    business_verdict_id: UUID = Field(foreign_key="business_verdicts.id", nullable=False)
    selected_action: CommercialNextStepAction = Field(max_length=64, nullable=False)
    accepted_conditions: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    override_reason: str | None = Field(default=None, max_length=2000)
    idempotency_key: str = Field(max_length=128, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
