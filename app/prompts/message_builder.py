"""Build LLM message lists from agent context and run input."""

from __future__ import annotations

import json
from typing import Any

from app.llm.contracts import LLMMessage
from app.prompts.agent_chat_workflow import (
    agent_chat_workflow_context_from_payload,
    build_agent_chat_workflow_system_content,
    supports_agent_chat_workflow,
)
from app.prompts.contracts import PromptBuildInput, PromptBuildOutput
from app.prompts.safety import (
    assert_no_prompt_secrets,
    format_context_block,
    sanitize_prompt_context,
)
from app.prompts.templates import resolve_system_prompt
from app.schemas.contracts import AgentType
from app.tools.agent_chat_tool_settings import (
    agent_chat_generate_assets_tools_enabled,
    agent_chat_plan_draft_tools_enabled,
    agent_chat_revision_tools_enabled,
)


def build_llm_messages(data: PromptBuildInput) -> PromptBuildOutput:
    assert_no_prompt_secrets(data.agent_config)
    assert_no_prompt_secrets(data.input_payload)
    if data.memory_context is not None:
        assert_no_prompt_secrets(data.memory_context)
    if data.user_context is not None:
        assert_no_prompt_secrets(data.user_context)

    sanitized_config = sanitize_prompt_context(data.agent_config)
    sanitized_input = sanitize_prompt_context(data.input_payload)
    sanitized_memory = (
        sanitize_prompt_context(data.memory_context) if data.memory_context is not None else None
    )
    sanitized_user_context = (
        sanitize_prompt_context(data.user_context) if data.user_context is not None else None
    )

    system_prompt, template_id = resolve_system_prompt(
        data.agent_type,
        sanitized_config if isinstance(sanitized_config, dict) else {},
        system_overrides=data.system_overrides,
    )

    messages: list[LLMMessage] = [LLMMessage(role="system", content=system_prompt)]

    workflow_context = (
        agent_chat_workflow_context_from_payload(sanitized_input)
        if isinstance(sanitized_input, dict)
        else None
    )
    revision_tools = agent_chat_revision_tools_enabled()
    if workflow_context is not None and supports_agent_chat_workflow(
        data.agent_type,
        revision_tools=revision_tools,
    ):
        messages.append(
            LLMMessage(
                role="system",
                content=build_agent_chat_workflow_system_content(
                    workflow_context,
                    plan_draft_tools=agent_chat_plan_draft_tools_enabled(),
                    generate_assets_tools=agent_chat_generate_assets_tools_enabled(),
                    revision_tools=revision_tools,
                    agent_type=data.agent_type,
                ),
            ),
        )

    if sanitized_memory is not None:
        messages.append(
            LLMMessage(
                role="system",
                content=format_context_block("Memory context", sanitized_memory),
            ),
        )

    raw_messages = sanitized_input.get("messages") if isinstance(sanitized_input, dict) else None
    if isinstance(raw_messages, list) and raw_messages:
        for item in raw_messages:
            messages.append(LLMMessage.model_validate(sanitize_prompt_context(item)))
    else:
        user_content = _build_user_content(
            sanitized_input if isinstance(sanitized_input, dict) else {},
            sanitized_user_context if isinstance(sanitized_user_context, dict) else None,
            agent_type=data.agent_type,
        )
        messages.append(LLMMessage(role="user", content=user_content))

    metadata = {
        "prompt_template_id": template_id,
        "agent_type": data.agent_type.value,
        "has_memory_context": sanitized_memory is not None,
        "message_count": len(messages),
        "input_keys": sorted(sanitized_input.keys()) if isinstance(sanitized_input, dict) else [],
    }
    assert_no_prompt_secrets(metadata)
    return PromptBuildOutput(messages=messages, metadata=metadata)


def _build_researcher_run_context(input_payload: dict[str, Any]) -> str | None:
    context_fields: dict[str, Any] = {}
    for key in ("brief_id", "funnel_id", "research_topic", "goal"):
        value = input_payload.get(key)
        if value is not None and str(value).strip():
            context_fields[key] = value
    if not context_fields:
        return None
    return format_context_block("Researcher run context", context_fields)


def _build_strategist_run_context(input_payload: dict[str, Any]) -> str | None:
    context_fields: dict[str, Any] = {}
    for key in ("brief_id", "funnel_id", "goal"):
        value = input_payload.get(key)
        if value is not None and str(value).strip():
            context_fields[key] = value
    if not context_fields:
        return None
    return format_context_block("Strategist run context", context_fields)


def _build_content_planner_run_context(input_payload: dict[str, Any]) -> str | None:
    context_fields: dict[str, Any] = {}
    for key in ("brief_id", "funnel_id", "goal"):
        value = input_payload.get(key)
        if value is not None and str(value).strip():
            context_fields[key] = value
    if not context_fields:
        return None
    return format_context_block("Content planner run context", context_fields)


def _build_critic_run_context(input_payload: dict[str, Any]) -> str | None:
    context_fields: dict[str, Any] = {}
    for key in ("brief_id", "funnel_id", "source_asset_id", "goal"):
        value = input_payload.get(key)
        if value is not None and str(value).strip():
            context_fields[key] = value
    if not context_fields:
        return None
    return format_context_block("Critic run context", context_fields)


def _build_orchestrator_run_context(input_payload: dict[str, Any]) -> str | None:
    context_fields: dict[str, Any] = {}
    for key in ("brief_id", "funnel_id", "goal", "research_topic"):
        value = input_payload.get(key)
        if value is not None and str(value).strip():
            context_fields[key] = value
    if not context_fields:
        return None
    return format_context_block("Orchestrator run context", context_fields)


def _build_copywriter_run_context(input_payload: dict[str, Any]) -> str | None:
    context_fields: dict[str, Any] = {}
    for key in (
        "brief_id",
        "funnel_id",
        "step_id",
        "source_asset_id",
        "asset_type",
        "title",
        "goal",
    ):
        value = input_payload.get(key)
        if value is not None and str(value).strip():
            context_fields[key] = value
    if not context_fields:
        return None
    return format_context_block("Copywriter run context", context_fields)


def _build_user_content(
    input_payload: dict[str, Any],
    user_context: dict[str, Any] | None,
    *,
    agent_type: AgentType | None = None,
) -> str:
    parts: list[str] = []
    prompt = input_payload.get("prompt")
    if prompt is not None:
        parts.append(str(prompt))
    elif input_payload:
        parts.append(json.dumps(input_payload, ensure_ascii=True, sort_keys=True))

    if agent_type == AgentType.STRATEGIST:
        strategist_context = _build_strategist_run_context(input_payload)
        if strategist_context:
            parts.append(strategist_context)

    if agent_type == AgentType.RESEARCHER:
        researcher_context = _build_researcher_run_context(input_payload)
        if researcher_context:
            parts.append(researcher_context)

    if agent_type == AgentType.COPYWRITER:
        copywriter_context = _build_copywriter_run_context(input_payload)
        if copywriter_context:
            parts.append(copywriter_context)

    if agent_type == AgentType.CONTENT_PLANNER:
        planner_context = _build_content_planner_run_context(input_payload)
        if planner_context:
            parts.append(planner_context)

    if agent_type == AgentType.CRITIC:
        critic_context = _build_critic_run_context(input_payload)
        if critic_context:
            parts.append(critic_context)

    if agent_type == AgentType.ORCHESTRATOR:
        orchestrator_context = _build_orchestrator_run_context(input_payload)
        if orchestrator_context:
            parts.append(orchestrator_context)

    if user_context:
        parts.append(format_context_block("User context", user_context))

    if not parts:
        return ""
    return "\n\n".join(parts)
