"""LLM request/response persistence — mirrors app.schemas.contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.schemas.contracts import LLMProvider, LLMRequestStatus


class LLMRequestTable(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "llm_requests"

    owner_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    project_id: UUID = Field(foreign_key="projects.id", index=True, nullable=False)
    agent_id: UUID = Field(foreign_key="agents.id", index=True, nullable=False)
    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True, nullable=False)
    task_id: UUID | None = Field(default=None, foreign_key="tasks.id", index=True)
    provider: LLMProvider = Field(index=True, nullable=False)
    model: str = Field(max_length=128, index=True, nullable=False)
    input_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    prompt_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    request_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    status: LLMRequestStatus = Field(
        default=LLMRequestStatus.QUEUED,
        index=True,
        nullable=False,
    )
    error: str | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)


class LLMResponseTable(UUIDPrimaryKeyMixin, SQLModel, table=True):
    __tablename__ = "llm_responses"
    __table_args__ = (UniqueConstraint("llm_request_id", name="uq_llm_responses_llm_request_id"),)

    llm_request_id: UUID = Field(foreign_key="llm_requests.id", index=True, nullable=False)
    output_payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    raw_response: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    input_tokens: int = Field(default=0, nullable=False)
    output_tokens: int = Field(default=0, nullable=False)
    total_tokens: int = Field(default=0, nullable=False)
    cost_estimate: float | None = Field(default=None)
    latency_ms: int | None = Field(default=None)
    response_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
