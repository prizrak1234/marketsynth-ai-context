"""Request bodies for CRUD API — optional fields for PATCH only."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.contracts import (
    AgentCapability,
    AgentRun,
    AgentType,
    BetaAccessStatus,
    LLMProvider,
    MemoryLayer,
    TaskStatus,
    UserRole,
)


class UserCreate(BaseModel):
    telegram_id: int | None = None
    email: str | None = None
    display_name: str | None = None
    role: UserRole = UserRole.MEMBER
    is_active: bool = True


class UserUpdate(BaseModel):
    telegram_id: int | None = None
    email: str | None = None
    display_name: str | None = None
    role: UserRole | None = None
    beta_access_status: BetaAccessStatus | None = None
    beta_notes: str | None = None


class ProjectCreate(BaseModel):
    owner_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    config: dict[str, Any] | None = None


class TaskCreate(BaseModel):
    project_id: UUID
    agent_id: UUID | None = None
    title: str = Field(min_length=1, max_length=512)
    status: TaskStatus = TaskStatus.PENDING
    input_payload: dict[str, Any] = Field(default_factory=dict)


class TaskUpdate(BaseModel):
    agent_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=512)
    status: TaskStatus | None = None
    input_payload: dict[str, Any] | None = None
    output_payload: dict[str, Any] | None = None
    completed_at: datetime | None = None


class MemoryItemCreate(BaseModel):
    user_id: UUID
    project_id: UUID | None = None
    layer: MemoryLayer
    key: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class MemoryItemCreateRequest(BaseModel):
    project_id: UUID | None = None
    layer: MemoryLayer
    key: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class MemoryItemUpdate(BaseModel):
    project_id: UUID | None = None
    layer: MemoryLayer | None = None
    key: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    metadata: dict[str, Any] | None = None
    expires_at: datetime | None = None


class AgentCreateRequest(BaseModel):
    project_id: UUID
    type: AgentType
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    config: dict[str, Any] | None = None
    capabilities: list[AgentCapability] | None = None


class AgentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    config: dict[str, Any] | None = None
    capabilities: list[AgentCapability] | None = None


class AgentRunCreateRequest(BaseModel):
    agent_id: UUID
    task_id: UUID | None = None
    parent_agent_run_id: UUID | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRunSucceededRequest(BaseModel):
    output_payload: dict[str, Any] = Field(default_factory=dict)


class AgentRunFailedRequest(BaseModel):
    error: str = Field(min_length=1)


class AgentRunReplayRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=256)


class LLMRequestCreateRequest(BaseModel):
    agent_run_id: UUID
    provider: LLMProvider
    model: str = Field(min_length=1, max_length=128)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    prompt_metadata: dict[str, Any] = Field(default_factory=dict)
    request_metadata: dict[str, Any] = Field(default_factory=dict)
    task_id: UUID | None = None


class LLMRequestFailedRequest(BaseModel):
    error: str = Field(min_length=1)


class ProjectWebhookCreateRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    subscribed_event_types: list[str] = Field(default_factory=list)


class ProjectWebhookRead(BaseModel):
    id: UUID
    project_id: UUID
    url: str
    subscribed_event_types: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProjectWebhookCreateResponse(BaseModel):
    webhook: ProjectWebhookRead
    signing_secret: str = Field(min_length=1)


class EventOutboxReplayResponse(BaseModel):
    event_id: UUID
    status: str
    replayed: bool


class AgentRunExecuteResponse(AgentRun):
    execution_engine: str = Field(min_length=1)


class LLMRequestSucceededRequest(BaseModel):
    output_payload: dict[str, Any] = Field(default_factory=dict)
    raw_response: dict[str, Any] = Field(default_factory=dict)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cost_estimate: float | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    response_metadata: dict[str, Any] = Field(default_factory=dict)
