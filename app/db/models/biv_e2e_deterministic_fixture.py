"""Internal E2E deterministic fixture — not part of public product contract."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now


class BivE2eDeterministicFixtureTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "biv_e2e_deterministic_fixtures"

    owner_id: UUID = Field(foreign_key="users.id", nullable=False, unique=True, index=True)
    outcome: str = Field(max_length=32, nullable=False)
    e2e_run_id: str = Field(max_length=128, nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
