"""Mutable execution context for LangGraph nodes — not part of graph state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_run import AgentRunTable
from app.graphs.checkpoints import GraphCheckpointStore, InMemoryGraphCheckpointStore
from app.llm.contracts import LLMGenerateOutput, LLMMessage
from app.schemas.contracts import LLMProvider
from app.services.agent_runs import AgentRunService
from app.services.llm_requests import LLMRequestService
from app.tools.audit_contracts import ToolAuditTracker
from app.tools.contracts import ToolCall, ToolDefinition, ToolResult


@dataclass
class GraphRunContext:
    session: AsyncSession
    owner_id: UUID
    run_id: UUID
    agent: Any
    run: AgentRunTable
    agent_runs: AgentRunService
    llm_requests: LLMRequestService
    provider: LLMProvider
    model: str
    temperature: float | None
    max_tokens: int | None
    adapter: Any
    available_tools: list[ToolDefinition]
    tool_choice: str | None
    permission_policy: dict[str, Any]
    provider_tools: list[ToolDefinition] | None
    llm_metadata: dict[str, Any]
    stored_input_payload: dict[str, Any]
    prompt_metadata: dict[str, Any]
    clean_input_payload: dict[str, Any] = field(default_factory=dict)
    memory_context: Any = None
    user_context: Any = None
    messages: list[LLMMessage] = field(default_factory=list)
    prompt_build_metadata: dict[str, Any] = field(default_factory=dict)
    tools_metadata: dict[str, Any] = field(default_factory=dict)
    initial_llm_request_id: UUID | None = None
    follow_up_llm_request_id: UUID | None = None
    follow_up_llm_response_id: UUID | None = None
    initial_llm_output: LLMGenerateOutput | None = None
    follow_up_llm_output: LLMGenerateOutput | None = None
    initial_tool_calls: list[ToolCall] = field(default_factory=list)
    tool_round_plan: Any = None
    tool_round_result: Any = None
    tool_results: list[ToolResult] = field(default_factory=list)
    budgeted_tool_results: list[ToolResult] = field(default_factory=list)
    audit_tracker: ToolAuditTracker | None = None
    trace_id: str = ""
    graph_version: str = "3.13"
    handoff_decision: Any = None
    max_steps: int = 10
    checkpoints_enabled: bool = True
    checkpoint_store: GraphCheckpointStore = field(default_factory=InMemoryGraphCheckpointStore)
