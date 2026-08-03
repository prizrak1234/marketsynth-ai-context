"""Mock LLM adapter — stable dry-run responses, no external APIs."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.llm.contracts import LLMGenerateInput, LLMGenerateOutput, LLMMessage
from app.llm.observability import (
    estimate_llm_cost,
    log_llm_event,
    measure_llm_call,
    metrics_from_output,
)
from app.marketing.content_plan_quality import (
    build_mock_content_plan_body,
    default_content_planner_draft_metadata,
)
from app.marketing.copy_quality import (
    build_mock_copy_draft_body,
    default_copywriter_draft_metadata,
)
from app.marketing.research_quality import (
    build_mock_research_body,
    default_researcher_draft_metadata,
)
from app.marketing.review_quality import (
    build_mock_review_body,
    default_critic_draft_metadata,
)
from app.marketing.strategy_contracts import (
    build_mock_strategy_draft_body,
    default_strategist_draft_metadata,
)
from app.schemas.contracts import AgentType, LLMProvider
from app.tools.contracts import ToolCall
from app.tools.parser import parse_tool_calls

MOCK_MODEL = "mock-model"
MOCK_CONTENT = "Mock LLM response"
MOCK_FINAL_CONTENT = "Mock LLM final answer after tools"
MOCK_STRATEGIST_FINAL_CONTENT = "Mock strategist final answer after tools"
MOCK_COPYWRITER_FINAL_CONTENT = "Mock copywriter final answer after tools"
MOCK_CONTENT_PLANNER_FINAL_CONTENT = "Mock content planner final answer after tools"
MOCK_CRITIC_FINAL_CONTENT = "Mock critic final answer after tools"
MOCK_RESEARCHER_FINAL_CONTENT = "Mock researcher final answer after tools"
MOCK_ORCHESTRATOR_FINAL_CONTENT = "Mock orchestrator final answer after handoff"

_MOCK_STRATEGY_DRAFT_BODY = build_mock_strategy_draft_body()


def _mock_tool_calls_from_metadata(metadata: dict[str, Any]) -> list[ToolCall] | None:
    raw = metadata.get("mock_tool_call")
    if raw is None:
        raw = metadata.get("debug_tool_call")
    if raw is None:
        return None
    if isinstance(raw, list):
        return parse_tool_calls(raw)
    return parse_tool_calls([raw])


def _is_copywriter_metadata(metadata: dict[str, Any]) -> bool:
    return (
        metadata.get("agent_type") == AgentType.COPYWRITER.value
        or metadata.get("mock_copywriter_flow") is True
    )


def _is_content_planner_metadata(metadata: dict[str, Any]) -> bool:
    return (
        metadata.get("agent_type") == AgentType.CONTENT_PLANNER.value
        or metadata.get("mock_content_planner_flow") is True
    )


def _is_critic_metadata(metadata: dict[str, Any]) -> bool:
    return (
        metadata.get("agent_type") == AgentType.CRITIC.value
        or metadata.get("mock_critic_flow") is True
    )


def _is_orchestrator_metadata(metadata: dict[str, Any]) -> bool:
    return (
        metadata.get("agent_type") == AgentType.ORCHESTRATOR.value
        or metadata.get("mock_orchestrator_flow") is True
    )


def _is_researcher_metadata(metadata: dict[str, Any]) -> bool:
    return (
        metadata.get("agent_type") == AgentType.RESEARCHER.value
        or metadata.get("mock_researcher_flow") is True
    )


def _build_create_draft_arguments(metadata: dict[str, Any]) -> dict[str, Any]:
    if _is_researcher_metadata(metadata):
        goal = str(metadata.get("goal") or "")
        research_topic = str(metadata.get("research_topic") or "")
        arguments: dict[str, Any] = {
            "type": str(metadata.get("default_asset_type", "article")),
            "title": str(metadata.get("default_asset_title", "Research Draft")),
            "body": build_mock_research_body(goal=goal, research_topic=research_topic),
            "metadata": default_researcher_draft_metadata(
                research_topic=research_topic,
                goal=goal,
            ),
        }
        brief_id = metadata.get("brief_id")
        if brief_id is not None:
            arguments["brief_id"] = str(brief_id)
        return arguments

    if _is_critic_metadata(metadata):
        goal = str(metadata.get("goal") or "")
        source_asset_id = metadata.get("source_asset_id")
        source_id_str = str(source_asset_id) if source_asset_id is not None else None
        arguments: dict[str, Any] = {
            "type": str(metadata.get("default_asset_type", "article")),
            "title": str(metadata.get("default_asset_title", "Content Review Draft")),
            "body": build_mock_review_body(goal=goal),
            "metadata": default_critic_draft_metadata(
                source_asset_id=source_id_str,
                goal=goal,
            ),
        }
        brief_id = metadata.get("brief_id")
        if brief_id is not None:
            arguments["brief_id"] = str(brief_id)
        return arguments

    if _is_content_planner_metadata(metadata):
        goal = str(metadata.get("goal") or "")
        funnel_id = metadata.get("funnel_id")
        funnel_id_str = str(funnel_id) if funnel_id is not None else None
        arguments: dict[str, Any] = {
            "type": str(metadata.get("default_asset_type", "article")),
            "title": str(metadata.get("default_asset_title", "Content Plan Draft")),
            "body": build_mock_content_plan_body(goal=goal),
            "metadata": default_content_planner_draft_metadata(
                funnel_id=funnel_id_str,
                goal=goal,
            ),
        }
        brief_id = metadata.get("brief_id")
        if brief_id is not None:
            arguments["brief_id"] = str(brief_id)
        return arguments

    if _is_copywriter_metadata(metadata):
        asset_type = str(metadata.get("asset_type") or metadata.get("default_asset_type", "email"))
        title = str(metadata.get("title") or metadata.get("default_asset_title", "Copy Draft"))
        goal = str(metadata.get("goal") or "")
        body = build_mock_copy_draft_body(asset_type, goal=goal)
        arguments: dict[str, Any] = {
            "type": asset_type,
            "title": title,
            "body": body,
            "metadata": default_copywriter_draft_metadata(goal=goal),
        }
        brief_id = metadata.get("brief_id")
        if brief_id is not None:
            arguments["brief_id"] = str(brief_id)
        return arguments

    arguments = {
        "type": str(metadata.get("default_asset_type", "article")),
        "title": str(metadata.get("default_asset_title", "Marketing Strategy Draft")),
        "body": _MOCK_STRATEGY_DRAFT_BODY,
        "metadata": default_strategist_draft_metadata(),
    }
    brief_id = metadata.get("brief_id")
    if brief_id is not None:
        arguments["brief_id"] = str(brief_id)
    return arguments


def _force_tool_call_arguments(tool_name: str, metadata: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "memory.search":
        return {"query": "mock"}
    if tool_name == "marketing_brief.get":
        brief_id = metadata.get("brief_id")
        if brief_id is not None:
            return {"brief_id": str(brief_id)}
        return {}
    if tool_name == "content_asset.get":
        source_asset_id = metadata.get("source_asset_id")
        if source_asset_id is not None:
            return {"asset_id": str(source_asset_id)}
        return {}
    if tool_name == "marketing_funnel.gap_analysis":
        funnel_id = metadata.get("funnel_id")
        if funnel_id is not None:
            return {"funnel_id": str(funnel_id)}
        return {}
    if tool_name == "marketing_funnel.get":
        funnel_id = metadata.get("funnel_id")
        if funnel_id is not None:
            return {"funnel_id": str(funnel_id), "include_steps": True}
        return {}
    if tool_name == "marketing_funnel.step_assets":
        step_id = metadata.get("step_id")
        if step_id is not None:
            return {"step_id": str(step_id)}
        return {}
    if tool_name == "content_asset.create_draft":
        return _build_create_draft_arguments(metadata)
    if tool_name == "campaign_plan_draft.create":
        project_id = metadata.get("project_id")
        campaign_id = metadata.get("campaign_id")
        agent_chat = metadata.get("agent_chat")
        if isinstance(agent_chat, dict) and agent_chat.get("campaign_id"):
            campaign_id = agent_chat.get("campaign_id")
        if project_id is None or campaign_id is None:
            return {}
        return {
            "project_id": str(project_id),
            "campaign_id": str(campaign_id),
            "title": str(metadata.get("default_plan_title", "Campaign plan draft")),
            "plan_payload": {
                "goal": str(metadata.get("goal") or "Campaign launch"),
                "target_audience": "Telegram subscribers",
                "key_message": "Product launch",
                "content_items": [
                    {
                        "title": "Launch post",
                        "channel": "telegram",
                        "format": "text",
                        "scheduled_at": "2026-06-04T15:00:00Z",
                        "notes": "Mock chat plan item",
                    },
                ],
            },
        }
    if tool_name == "campaign_plan_draft.generate_assets":
        agent_chat = metadata.get("agent_chat")
        campaign_id = metadata.get("campaign_id")
        draft_id = metadata.get("draft_id")
        if isinstance(agent_chat, dict):
            campaign_id = agent_chat.get("campaign_id") or campaign_id
        if campaign_id is None or draft_id is None:
            return {}
        return {
            "campaign_id": str(campaign_id),
            "draft_id": str(draft_id),
        }
    if tool_name == "content_asset.create_revision":
        project_id = metadata.get("project_id")
        asset_id = metadata.get("asset_id")
        if project_id is None or asset_id is None:
            return {}
        return {
            "project_id": str(project_id),
            "asset_id": str(asset_id),
            "body": str(
                metadata.get(
                    "revision_body",
                    "Улучшенный текст поста для Telegram. Больше выгод и чёткий CTA.",
                ),
            ),
        }
    return {}


def _force_tool_call_from_metadata(metadata: dict[str, Any]) -> list[ToolCall] | None:
    force_tool = metadata.get("force_tool_call")
    if not force_tool:
        return None
    tool_name = str(force_tool)
    return [
        ToolCall(
            id="call_force_mock",
            name=tool_name,
            arguments=_force_tool_call_arguments(tool_name, metadata),
        ),
    ]


def _mock_copywriter_flow_tool_calls(metadata: dict[str, Any]) -> list[ToolCall] | None:
    if not metadata.get("mock_copywriter_flow"):
        return None

    calls: list[ToolCall] = []
    brief_id = metadata.get("brief_id")
    if brief_id is not None:
        calls.append(
            ToolCall(
                id="call_mock_copy_brief",
                name="marketing_brief.get",
                arguments={"brief_id": str(brief_id)},
            ),
        )

    step_id = metadata.get("step_id")
    if step_id is not None:
        calls.append(
            ToolCall(
                id="call_mock_copy_step",
                name="marketing_funnel.step_assets",
                arguments={"step_id": str(step_id)},
            ),
        )

    from app.tools.write_tool_settings import content_asset_create_draft_enabled

    if content_asset_create_draft_enabled():
        calls.append(
            ToolCall(
                id="call_mock_copy_draft",
                name="content_asset.create_draft",
                arguments=_build_create_draft_arguments(metadata),
            ),
        )

    return calls


def _mock_content_planner_flow_tool_calls(metadata: dict[str, Any]) -> list[ToolCall] | None:
    if not metadata.get("mock_content_planner_flow"):
        return None

    calls: list[ToolCall] = []
    funnel_id = metadata.get("funnel_id")
    if funnel_id is not None:
        calls.append(
            ToolCall(
                id="call_mock_planner_gap",
                name="marketing_funnel.gap_analysis",
                arguments={"funnel_id": str(funnel_id)},
            ),
        )

    from app.tools.write_tool_settings import content_asset_create_draft_enabled

    if content_asset_create_draft_enabled():
        calls.append(
            ToolCall(
                id="call_mock_planner_draft",
                name="content_asset.create_draft",
                arguments=_build_create_draft_arguments(metadata),
            ),
        )

    if not calls:
        return None
    return calls


def _mock_critic_flow_tool_calls(metadata: dict[str, Any]) -> list[ToolCall] | None:
    if not metadata.get("mock_critic_flow"):
        return None

    calls: list[ToolCall] = []
    source_asset_id = metadata.get("source_asset_id")
    if source_asset_id is not None:
        calls.append(
            ToolCall(
                id="call_mock_critic_asset",
                name="content_asset.get",
                arguments={"asset_id": str(source_asset_id)},
            ),
        )

    brief_id = metadata.get("brief_id")
    if brief_id is not None:
        calls.append(
            ToolCall(
                id="call_mock_critic_brief",
                name="marketing_brief.get",
                arguments={"brief_id": str(brief_id)},
            ),
        )

    from app.tools.write_tool_settings import content_asset_create_draft_enabled

    if content_asset_create_draft_enabled():
        calls.append(
            ToolCall(
                id="call_mock_critic_draft",
                name="content_asset.create_draft",
                arguments=_build_create_draft_arguments(metadata),
            ),
        )

    if not calls:
        return None
    return calls


def _mock_orchestrator_flow_tool_calls(metadata: dict[str, Any]) -> list[ToolCall] | None:
    if not metadata.get("mock_orchestrator_flow"):
        return None

    calls: list[ToolCall] = [
        ToolCall(
            id="call_mock_orch_context",
            name="project_context.get",
            arguments={},
        ),
    ]
    funnel_id = metadata.get("funnel_id")
    if funnel_id is not None:
        calls.append(
            ToolCall(
                id="call_mock_orch_gap",
                name="marketing_funnel.gap_analysis",
                arguments={"funnel_id": str(funnel_id)},
            ),
        )
    return calls


def _mock_researcher_flow_tool_calls(metadata: dict[str, Any]) -> list[ToolCall] | None:
    if not metadata.get("mock_researcher_flow"):
        return None

    calls: list[ToolCall] = []
    brief_id = metadata.get("brief_id")
    if brief_id is not None:
        calls.append(
            ToolCall(
                id="call_mock_research_brief",
                name="marketing_brief.get",
                arguments={"brief_id": str(brief_id)},
            ),
        )

    funnel_id = metadata.get("funnel_id")
    if funnel_id is not None:
        calls.append(
            ToolCall(
                id="call_mock_research_gap",
                name="marketing_funnel.gap_analysis",
                arguments={"funnel_id": str(funnel_id)},
            ),
        )

    research_topic = metadata.get("research_topic")
    if research_topic is not None and str(research_topic).strip():
        calls.append(
            ToolCall(
                id="call_mock_research_memory",
                name="memory.search",
                arguments={"query": str(research_topic).strip()},
            ),
        )

    from app.tools.write_tool_settings import content_asset_create_draft_enabled

    if content_asset_create_draft_enabled():
        calls.append(
            ToolCall(
                id="call_mock_research_draft",
                name="content_asset.create_draft",
                arguments=_build_create_draft_arguments(metadata),
            ),
        )

    if not calls:
        return None
    return calls


def _mock_strategy_flow_tool_calls(metadata: dict[str, Any]) -> list[ToolCall] | None:
    if not metadata.get("mock_strategy_flow"):
        return None

    calls: list[ToolCall] = []
    funnel_id = metadata.get("funnel_id")
    gap_arguments: dict[str, Any] = {}
    if funnel_id is not None:
        gap_arguments["funnel_id"] = str(funnel_id)
    calls.append(
        ToolCall(
            id="call_mock_strategy_gap",
            name="marketing_funnel.gap_analysis",
            arguments=gap_arguments,
        ),
    )

    from app.tools.write_tool_settings import content_asset_create_draft_enabled

    if content_asset_create_draft_enabled():
        calls.append(
            ToolCall(
                id="call_mock_strategy_draft",
                name="content_asset.create_draft",
                arguments=_build_create_draft_arguments(metadata),
            ),
        )

    return calls


def _has_tool_result_messages(messages: list[LLMMessage]) -> bool:
    return any(message.role == "tool" for message in messages)


def _final_content(metadata: dict[str, Any]) -> str:
    if metadata.get("agent_type") == AgentType.COPYWRITER.value:
        return MOCK_COPYWRITER_FINAL_CONTENT
    if metadata.get("agent_type") == AgentType.CONTENT_PLANNER.value:
        return MOCK_CONTENT_PLANNER_FINAL_CONTENT
    if metadata.get("agent_type") == AgentType.CRITIC.value:
        return MOCK_CRITIC_FINAL_CONTENT
    if metadata.get("agent_type") == AgentType.RESEARCHER.value:
        return MOCK_RESEARCHER_FINAL_CONTENT
    if metadata.get("agent_type") == AgentType.STRATEGIST.value:
        return MOCK_STRATEGIST_FINAL_CONTENT
    if _is_orchestrator_metadata(metadata):
        return MOCK_ORCHESTRATOR_FINAL_CONTENT
    return MOCK_FINAL_CONTENT


class MockLLMAdapter:
    async def generate(self, data: LLMGenerateInput) -> LLMGenerateOutput:
        metadata = data.metadata or {}
        if _has_tool_result_messages(data.messages):
            return await self._build_output(
                data,
                content=_final_content(metadata),
                tool_calls=None,
                finish_reason="stop",
            )

        tool_calls = _mock_tool_calls_from_metadata(metadata)
        if tool_calls is None:
            tool_calls = _force_tool_call_from_metadata(metadata)
        if tool_calls is None:
            tool_calls = _mock_orchestrator_flow_tool_calls(metadata)
        if tool_calls is None:
            tool_calls = _mock_copywriter_flow_tool_calls(metadata)
        if tool_calls is None:
            tool_calls = _mock_content_planner_flow_tool_calls(metadata)
        if tool_calls is None:
            tool_calls = _mock_critic_flow_tool_calls(metadata)
        if tool_calls is None:
            tool_calls = _mock_researcher_flow_tool_calls(metadata)
        if tool_calls is None:
            tool_calls = _mock_strategy_flow_tool_calls(metadata)

        if tool_calls:
            return await self._build_output(
                data,
                content="",
                tool_calls=tool_calls,
                finish_reason="tool_calls",
            )

        if metadata.get("user_request_general_answer"):
            user_text = ""
            for message in reversed(data.messages):
                if message.role == "user" and message.content:
                    user_text = message.content.strip()
                    break
            if metadata.get("force_empty_response"):
                content = "   "
            else:
                content = (
                    f"Ответ Marketsynth (mock): {user_text[:400]}"
                    if user_text
                    else "Ответ Marketsynth (mock): пустой вопрос."
                )
            return await self._build_output(
                data,
                content=content,
                tool_calls=None,
                finish_reason="stop",
            )

        return await self._build_output(
            data,
            content=MOCK_CONTENT,
            tool_calls=None,
            finish_reason="stop",
        )

    async def _build_output(
        self,
        data: LLMGenerateInput,
        *,
        content: str,
        tool_calls: list[ToolCall] | None,
        finish_reason: str | None,
    ) -> LLMGenerateOutput:
        async with measure_llm_call(provider=data.provider, model=data.model) as retry_state:
            retry_state["retry_count"] = 0
            output = LLMGenerateOutput(
                content=content,
                raw_response={},
                usage={
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                },
                model=data.model,
                provider=LLMProvider.MOCK,
                latency_ms=int((time.perf_counter() - retry_state["started_at"]) * 1000),
                retry_count=0,
                estimated_cost_usd=estimate_llm_cost(
                    provider=data.provider,
                    model=data.model,
                    prompt_tokens=0,
                    completion_tokens=0,
                ),
                tool_calls=tool_calls,
                finish_reason=finish_reason,
            )
        log_llm_event("llm.call.succeeded", metrics_from_output(output).to_log_payload())
        return output


def build_messages(input_payload: dict[str, Any]) -> list[LLMMessage]:
    """Legacy helper for tests — delegates to the prompt builder layer."""
    from app.prompts.contracts import PromptBuildInput
    from app.prompts.message_builder import build_llm_messages

    built = build_llm_messages(
        PromptBuildInput(
            agent_id=uuid4(),
            agent_type=AgentType.RESEARCHER,
            agent_config={},
            input_payload=input_payload or {},
        ),
    )
    return built.messages
