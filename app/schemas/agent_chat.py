"""Agent chat API schemas (Phase AI.1)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field

from app.schemas.contracts import (
    AgentChatMessage,
    AgentChatMessageRole,
    AgentChatSession,
    ChatAssistantMessageBlock,
    ChatAuditEventType,
    ChatBlockActionType,
    ChatSessionDomain,
    ChatSessionEntrypoint,
)


class AgentChatSendRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=32000,
        validation_alias=AliasChoices("message", "content"),
    )
    session_id: UUID | None = None
    agent_id: UUID | None = None
    campaign_id: UUID | None = None


class AgentChatPlanDraftCreated(BaseModel):
    draft_id: UUID
    campaign_id: UUID
    title: str | None = None


class AgentChatGeneratedAssets(BaseModel):
    campaign_id: UUID
    draft_id: UUID
    created_count: int
    already_generated: bool
    asset_ids: list[UUID]


class AgentChatRevisedAsset(BaseModel):
    asset_id: UUID
    version: int


class AgentChatSubagentExecution(BaseModel):
    subagent: str
    agent_run_id: UUID


class AgentChatSubagentChainEntry(BaseModel):
    subagent: str
    agent_run_id: UUID
    status: str | None = None


class AgentChatGeneralDelegation(BaseModel):
    domain: str
    agent_run_id: UUID


class AgentChatExecutionMetadata(BaseModel):
    entrypoint: str
    domain: str


class ChatBlockActionRequest(BaseModel):
    session_id: UUID
    assistant_message_id: UUID
    block_index: int = Field(ge=0)
    action_type: ChatBlockActionType
    payload: dict[str, object] | None = None


class ChatBlockActionResponse(BaseModel):
    status: str
    message: str
    created_resource_type: str | None = None
    created_resource_id: UUID | None = None
    text: str | None = None
    markdown: str | None = None


class AgentChatMessageSearchHit(BaseModel):
    message_id: UUID
    session_id: UUID
    session_title: str | None = None
    role: AgentChatMessageRole
    content_preview: str
    created_at: datetime
    domain: ChatSessionDomain
    entrypoint: ChatSessionEntrypoint


class ChatAuditEventRead(BaseModel):
    id: UUID
    owner_id: UUID
    project_id: UUID
    session_id: UUID | None = None
    message_id: UUID | None = None
    agent_id: UUID | None = None
    event_type: ChatAuditEventType
    domain: ChatSessionDomain
    entrypoint: ChatSessionEntrypoint
    status: str
    safe_metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class AgentChatMetricsResponse(BaseModel):
    sessions_total: int = 0
    sessions_active: int = 0
    sessions_archived: int = 0
    messages_total: int = 0
    messages_user: int = 0
    messages_assistant: int = 0
    runs_total: int = 0
    runs_succeeded: int = 0
    runs_failed: int = 0
    block_actions_total: int = 0
    block_actions_by_type: dict[str, int] = Field(default_factory=dict)
    searches_total: int = 0
    searches_by_type: dict[str, int] = Field(default_factory=dict)
    sessions_by_domain: dict[str, int] = Field(default_factory=dict)
    messages_by_domain: dict[str, int] = Field(default_factory=dict)
    latest_activity_at: datetime | None = None


class AgentChatSendResponse(BaseModel):
    session: AgentChatSession
    session_id: UUID
    user_message: AgentChatMessage
    assistant_message: AgentChatMessage
    assistant_message_id: UUID
    agent_run_id: UUID
    output: dict[str, object] = Field(default_factory=dict)
    blocks: list[ChatAssistantMessageBlock] = Field(default_factory=list)
    plan_draft: AgentChatPlanDraftCreated | None = None
    generated_assets: AgentChatGeneratedAssets | None = None
    revised_assets: list[AgentChatRevisedAsset] | None = None
    subagent_execution: AgentChatSubagentExecution | None = None
    subagent_chain: list[AgentChatSubagentChainEntry] | None = None
    general_delegation: AgentChatGeneralDelegation | None = None
    execution_metadata: AgentChatExecutionMetadata | None = None
