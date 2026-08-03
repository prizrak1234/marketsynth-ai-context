"""LangGraph agent run state contracts — no secrets in graph state."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, TypedDict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.db.base import utc_now
from app.schemas.contracts import AgentRunStatus
from app.tools.security import find_forbidden_tool_key

GRAPH_CONTEXT_CONFIG_KEY = "graph_run_context"

CHECKPOINT_STATE_KEYS = frozenset(
    {
        "owner_id",
        "project_id",
        "agent_id",
        "agent_run_id",
        "task_id",
        "input_payload",
        "messages",
        "tool_results",
        "output_payload",
        "status",
        "error",
        "has_tool_calls",
        "follow_up_llm_call",
        "pending_tool_calls",
        "tool_calls_planned",
        "tool_calls_executed",
        "tool_calls_skipped",
        "tool_round_status",
        "memory_load_status",
        "memory_item_count",
        "memory_query",
        "memory_context",
        "handoff_status",
        "handoff_target_agent_id",
        "handoff_target_agent_type",
        "handoff_reason",
        "child_agent_run_id",
        "child_run_enqueued",
        "child_run_executed",
        "graph_version",
        "current_node",
        "completed_nodes",
        "failed_node",
        "node_errors",
        "started_at",
        "finished_at",
        "trace_id",
        "step_count",
        "max_steps",
    },
)


class AgentGraphStateDict(TypedDict, total=False):
    """LangGraph channel schema — fields persist across nodes when declared here."""

    owner_id: str
    project_id: str
    agent_id: str
    agent_run_id: str
    task_id: str | None
    input_payload: dict[str, Any]
    messages: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    output_payload: dict[str, Any]
    status: str
    error: str | None
    has_tool_calls: bool
    follow_up_llm_call: bool
    pending_tool_calls: list[dict[str, Any]]
    tool_calls_planned: int
    tool_calls_executed: int
    tool_calls_skipped: int
    tool_round_status: str | None
    memory_load_status: str | None
    memory_item_count: int
    memory_query: str | None
    memory_context: dict[str, Any] | list[Any] | None
    handoff_status: str | None
    handoff_target_agent_id: str | None
    handoff_target_agent_type: str | None
    handoff_reason: str | None
    child_agent_run_id: str | None
    child_run_enqueued: bool
    child_run_executed: bool
    graph_version: str
    current_node: str | None
    completed_nodes: list[str]
    failed_node: str | None
    node_errors: list[dict[str, Any]]
    started_at: str | None
    finished_at: str | None
    trace_id: str
    step_count: int
    max_steps: int


class AgentGraphState(BaseModel):
    """Serializable graph state — must not carry API keys or credentials."""

    owner_id: UUID
    project_id: UUID
    agent_id: UUID
    agent_run_id: UUID
    task_id: UUID | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    status: AgentRunStatus = AgentRunStatus.RUNNING
    error: str | None = None
    has_tool_calls: bool = False
    follow_up_llm_call: bool = False
    pending_tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls_planned: int = 0
    tool_calls_executed: int = 0
    tool_calls_skipped: int = 0
    tool_round_status: str | None = None
    memory_load_status: str | None = None
    memory_item_count: int = 0
    memory_query: str | None = None
    memory_context: dict[str, Any] | list[Any] | None = None
    handoff_status: str | None = None
    handoff_target_agent_id: str | None = None
    handoff_target_agent_type: str | None = None
    handoff_reason: str | None = None
    child_agent_run_id: str | None = None
    child_run_enqueued: bool = False
    child_run_executed: bool = False
    graph_version: str = "3.13"
    current_node: str | None = None
    completed_nodes: list[str] = Field(default_factory=list)
    failed_node: str | None = None
    node_errors: list[dict[str, Any]] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    step_count: int = 0
    max_steps: int = 10

    def to_graph_dict(self) -> AgentGraphStateDict:
        return self.model_dump(mode="json")  # type: ignore[return-value]

    @classmethod
    def from_graph_dict(cls, data: dict[str, Any]) -> AgentGraphState:
        return cls.model_validate(data)

    @classmethod
    def create_initial(
        cls,
        *,
        owner_id: UUID,
        project_id: UUID,
        agent_id: UUID,
        agent_run_id: UUID,
        input_payload: dict[str, Any],
        task_id: UUID | None = None,
        graph_version: str,
        trace_id: str,
        max_steps: int,
    ) -> AgentGraphState:
        return cls(
            owner_id=owner_id,
            project_id=project_id,
            agent_id=agent_id,
            agent_run_id=agent_run_id,
            task_id=task_id,
            input_payload=input_payload,
            status=AgentRunStatus.RUNNING,
            graph_version=graph_version,
            trace_id=trace_id,
            max_steps=max_steps,
            step_count=0,
            started_at=utc_now(),
        )


def state_snapshot_for_checkpoint(state: AgentGraphStateDict) -> dict[str, Any]:
    """Return a checkpoint-safe subset of graph state (no services or raw provider payloads)."""
    snapshot: dict[str, Any] = {}
    for key in CHECKPOINT_STATE_KEYS:
        if key in state:
            snapshot[key] = state[key]
    return snapshot


def _scan_payload_for_secrets(payload: dict[str, Any] | list[Any]) -> None:
    forbidden = find_forbidden_tool_key(payload)
    if forbidden is not None:
        raise ValueError(f"Graph state contains forbidden key: {forbidden}")


def assert_no_graph_state_secrets(state: AgentGraphState | AgentGraphStateDict) -> None:
    """Reject state payloads that embed credential-like keys or values."""
    if isinstance(state, AgentGraphState):
        data: dict[str, Any] = state.model_dump(mode="json")
    else:
        data = dict(state)

    _scan_payload_for_secrets(data.get("input_payload", {}))
    _scan_payload_for_secrets(data.get("output_payload", {}))
    _scan_payload_for_secrets(data.get("messages", []))
    _scan_payload_for_secrets(data.get("tool_results", []))
    _scan_payload_for_secrets(data.get("pending_tool_calls", []))
    memory_ctx = data.get("memory_context")
    if memory_ctx is not None:
        _scan_payload_for_secrets(memory_ctx)
    handoff_reason = data.get("handoff_reason")
    if handoff_reason:
        _scan_payload_for_secrets({"reason": handoff_reason})
    _scan_payload_for_secrets(data.get("node_errors", []))

    for forbidden_key in ("raw_response", "session", "adapter", "checkpoint_store"):
        if forbidden_key in data:
            raise ValueError(f"Graph state must not include forbidden key: {forbidden_key}")

    serialized = json.dumps(data, ensure_ascii=True).lower()
    for marker in ("sk-", "api_key", "authorization", "bearer "):
        if marker in serialized:
            raise ValueError(f"Graph state contains forbidden marker: {marker}")


def assert_agent_graph_state_has_no_secrets(state: AgentGraphState) -> None:
    """Backward-compatible alias for Phase 3.0 tests."""
    assert_no_graph_state_secrets(state)
