"""Marketing campaigns persistence — campaign container skeleton (Phase 9.0)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, Text
from sqlalchemy.types import JSON
from sqlmodel import Field

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.marketing.contracts import MarketingCampaignStatus


class MarketingCampaignTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "marketing_campaigns"
    __table_args__ = (
        Index("ix_marketing_campaigns_owner_id", "owner_id"),
        Index("ix_marketing_campaigns_project_id", "project_id"),
        Index("ix_marketing_campaigns_brief_id", "brief_id"),
        Index("ix_marketing_campaigns_status", "status"),
        Index("ix_marketing_campaigns_created_at", "created_at"),
    )

    owner_id: UUID = Field(foreign_key="users.id", nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", nullable=False)
    brief_id: UUID | None = Field(
        default=None,
        foreign_key="marketing_briefs.id",
        nullable=True,
    )

    title: str = Field(max_length=512, nullable=False)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    status: MarketingCampaignStatus = Field(
        default=MarketingCampaignStatus.DRAFT,
        nullable=False,
    )

    start_at: datetime | None = Field(default=None, nullable=True)
    end_at: datetime | None = Field(default=None, nullable=True)

    campaign_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("campaign_metadata", JSON, nullable=False),
    )

