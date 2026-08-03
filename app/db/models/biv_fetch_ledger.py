"""BIV fetch ledger — immutable per-attempt URL fetch audit."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.db.base import UUIDPrimaryKeyMixin, utc_now


class BivFetchLedgerTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "biv_fetch_ledger_entries"
    __table_args__ = (
        Index("ix_biv_fetch_ledger_run", "run_id"),
        Index("ix_biv_fetch_ledger_correlation", "correlation_id"),
        Index("ix_biv_fetch_ledger_normalized_url", "run_id", "normalized_url"),
    )

    run_id: UUID = Field(foreign_key="business_idea_validation_runs.id", nullable=False)
    correlation_id: str = Field(max_length=128, nullable=False)
    query_id: str = Field(default="", max_length=128, nullable=False)
    source_url: str = Field(max_length=2048, nullable=False)
    normalized_url: str = Field(max_length=2048, nullable=False)
    provider: str = Field(max_length=64, nullable=False)
    attempt_number: int = Field(default=1, nullable=False)
    started_at: datetime = Field(nullable=False)
    finished_at: datetime = Field(nullable=False)
    latency_ms: int = Field(default=0, nullable=False)
    http_status: int | None = Field(default=None)
    outcome_code: str = Field(max_length=64, nullable=False)
    content_type: str | None = Field(default=None, max_length=128)
    content_length: int | None = Field(default=None)
    retryable: bool = Field(default=False, nullable=False)
    fallback_used: bool = Field(default=False, nullable=False)
    error_class: str | None = Field(default=None, max_length=64)
    safe_error_message: str | None = Field(default=None, max_length=500)
    raw_content_stored: bool = Field(default=False, nullable=False)
    extracted_text_length: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
