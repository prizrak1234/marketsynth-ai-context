"""Build AgentRun input payloads for agent chat (Phase AI.3)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.tools.agent_chat_tool_settings import (
    agent_chat_generate_assets_tools_enabled,
    agent_chat_plan_draft_tools_enabled,
    agent_chat_revision_tools_enabled,
)


def build_agent_chat_run_input_payload(
    *,
    prompt: str,
    project_id: UUID,
    workflow_context: dict[str, object] | None,
    revision_context: dict[str, object] | None = None,
    scenario_context: dict[str, object] | None = None,
    subagent_routing: dict[str, object] | None = None,
    session_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"prompt": prompt}
    if session_history:
        payload["messages"] = session_history
    if workflow_context is not None:
        agent_chat = dict(workflow_context)
        if (
            agent_chat_plan_draft_tools_enabled()
            or agent_chat_revision_tools_enabled()
        ):
            payload["project_id"] = str(project_id)
        if agent_chat_plan_draft_tools_enabled():
            agent_chat["plan_draft_create_enabled"] = True
        if agent_chat_generate_assets_tools_enabled():
            agent_chat["generate_assets_enabled"] = True
        if agent_chat_revision_tools_enabled():
            agent_chat["revision_tools_enabled"] = True
        if revision_context is not None:
            agent_chat["revision_context"] = revision_context
        if scenario_context is not None:
            agent_chat["scenario_context"] = scenario_context
        if subagent_routing is not None:
            agent_chat["subagent_routing"] = subagent_routing
        payload["agent_chat"] = agent_chat
    return payload
