"""LLM adapter metadata for agent runs (mock flows, debug hooks)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.schemas.contracts import AgentType


def build_llm_run_metadata(
    run_id: UUID,
    *,
    agent_type: AgentType | None = None,
    agent_config: dict[str, Any] | None = None,
    input_payload: dict[str, Any] | None = None,
    mock_tool_call: Any = None,
    debug_tool_call: Any = None,
    force_tool_call: Any = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {"agent_run_id": str(run_id)}

    if agent_type is not None:
        metadata["agent_type"] = agent_type.value

    config = agent_config if isinstance(agent_config, dict) else {}
    if config.get("mock_strategy_flow") is True:
        metadata["mock_strategy_flow"] = True
    if config.get("mock_copywriter_flow") is True:
        metadata["mock_copywriter_flow"] = True
    if config.get("mock_content_planner_flow") is True:
        metadata["mock_content_planner_flow"] = True
    if config.get("mock_critic_flow") is True:
        metadata["mock_critic_flow"] = True
    if config.get("mock_researcher_flow") is True:
        metadata["mock_researcher_flow"] = True
    if config.get("mock_orchestrator_flow") is True:
        metadata["mock_orchestrator_flow"] = True

    output_cfg = config.get("output")
    if isinstance(output_cfg, dict):
        for key in ("default_asset_type", "default_asset_title"):
            value = output_cfg.get(key)
            if value is not None:
                metadata[key] = value

    payload = input_payload if isinstance(input_payload, dict) else {}
    for key in (
        "brief_id",
        "funnel_id",
        "step_id",
        "source_asset_id",
        "asset_type",
        "title",
        "research_topic",
        "goal",
        "project_id",
    ):
        value = payload.get(key)
        if value is not None:
            metadata[key] = value

    agent_chat = payload.get("agent_chat")
    if isinstance(agent_chat, dict):
        metadata["agent_chat"] = agent_chat
        campaign_id = agent_chat.get("campaign_id")
        if campaign_id is not None:
            metadata["campaign_id"] = campaign_id

    if mock_tool_call is not None:
        metadata["mock_tool_call"] = mock_tool_call
    if debug_tool_call is not None:
        metadata["debug_tool_call"] = debug_tool_call
    if force_tool_call is not None:
        metadata["force_tool_call"] = force_tool_call

    return metadata
