"""LangGraph conditional routing for agent run execution."""

from __future__ import annotations

from typing import Literal

from app.graphs.contracts import AgentGraphStateDict
from app.graphs.handoff import HANDOFF_STATUS_DELEGATED
from app.schemas.contracts import AgentRunStatus


def _is_failed(state: AgentGraphStateDict) -> bool:
    if state.get("error"):
        return True
    status = state.get("status")
    return status in {AgentRunStatus.FAILED.value, AgentRunStatus.FAILED}


def route_after_handoff_gate(
    state: AgentGraphStateDict,
) -> Literal["handoff_record", "build_prompt", "final_response"]:
    if _is_failed(state):
        return "final_response"
    if state.get("handoff_status") == HANDOFF_STATUS_DELEGATED:
        return "handoff_record"
    return "build_prompt"


def route_after_llm_call(
    state: AgentGraphStateDict,
) -> Literal["tool_prepare", "final_response"]:
    if _is_failed(state):
        return "final_response"
    if state.get("has_tool_calls"):
        return "tool_prepare"
    return "final_response"


def route_after_tool_prepare(
    state: AgentGraphStateDict,
) -> Literal["tool_execute", "final_response"]:
    if _is_failed(state):
        return "final_response"
    planned = int(state.get("tool_calls_planned") or 0)
    if planned <= 0:
        return "final_response"
    return "tool_execute"


def route_after_tool_execute(
    state: AgentGraphStateDict,
) -> Literal["tool_finalize", "final_response"]:
    if _is_failed(state):
        return "final_response"
    return "tool_finalize"


def route_after_tool_finalize(
    state: AgentGraphStateDict,
) -> Literal["llm_follow_up", "final_response"]:
    if _is_failed(state):
        return "final_response"
    if not state.get("follow_up_llm_call"):
        return "final_response"
    return "llm_follow_up"


def route_after_llm_follow_up(state: AgentGraphStateDict) -> Literal["final_response"]:
    return "final_response"
