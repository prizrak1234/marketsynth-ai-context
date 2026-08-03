"""Agent chat workflow context formatting (Phase AI.2)."""

from __future__ import annotations

from typing import Any

from app.agents.marketer.contracts import MarketerSubAgentType
from app.prompts.safety import format_context_block
from app.schemas.contracts import AgentType, CampaignWorkflowState
from app.services.agent_chat_revision import AGENT_CHAT_CAMPAIGN_REVISION_MAX_ASSETS

_AGENT_CHAT_ADVISOR_TYPES = frozenset(
    {
        AgentType.STRATEGIST,
        AgentType.ORCHESTRATOR,
        AgentType.CONTENT_PLANNER,
    },
)

_AGENT_CHAT_ADVISOR_RULES = (
    "Agent chat mode — advisory only:\n"
    "- Use the provided campaign workflow context; do not invent workflow state.\n"
    "- Never claim a plan, asset, or publication job was created unless a tool/API "
    "result confirms it.\n"
    "- You cannot execute write actions in chat; guide the human to the product UI.\n"
    "- Give one clear next safe step aligned with next_recommended_action."
)

_AGENT_CHAT_PLAN_DRAFT_RULES = (
    "Agent chat with gated plan draft tools:\n"
    "- Use campaign_plan_draft.create only for the campaign_id in workflow context.\n"
    "- You may read marketing_campaign.get and marketing_campaign.workflow first.\n"
    "- Never claim a draft was created unless campaign_plan_draft.create succeeds.\n"
    "- Do not approve assets, schedule, or publish from chat.\n"
    "- After a successful create, tell the user the draft_id and that Generate Assets "
    "is the next step in the campaign UI."
)

_AGENT_CHAT_GENERATE_ASSETS_RULES = (
    "Agent chat with gated generate-assets tool:\n"
    "- Use campaign_plan_draft.generate_assets only for the selected campaign_id "
    "and an existing draft_id.\n"
    "- Never pass project_id; scope comes from the chat run context.\n"
    "- Never claim assets were created unless campaign_plan_draft.generate_assets succeeds.\n"
    "- Do not approve, schedule, or publish from chat.\n"
    "- After success, direct the user to Review Queue to review draft assets."
)

_AGENT_CHAT_REVISION_RULES = (
    "Agent chat with gated content revision tools:\n"
    "- Read campaign context (marketing_campaign.get, marketing_campaign.overview, "
    "marketing_campaign.workflow) before rewriting.\n"
    "- Use content_asset.get to read the current asset body before rewriting.\n"
    "- Use campaign_asset.list to find draft assets for a campaign (status=draft).\n"
    "- Use content_asset.create_revision with project_id, asset_id, and the full "
    "rewritten body (instruction from the user is not a tool argument).\n"
    "- For campaign-wide requests, revise at most 20 draft assets per run.\n"
    "- Never approve, schedule, publish, or archive from chat.\n"
    "- Never claim a revision unless content_asset.create_revision succeeds.\n"
    "- After success, direct the user to Review Queue."
)

_AGENT_CHAT_ORCHESTRATOR_SCENARIO_RULES = (
    "Marketing orchestrator scenario mode:\n"
    "- When a marketing scenario is detected, act as a marketing coordinator.\n"
    "- Use marketing_campaign.workflow, marketing_campaign.overview, review_queue.list, "
    "and publication_calendar.list when tools are available — never invent counts.\n"
    "- Propose the numbered recommended_next_steps from the scenario context block.\n"
    "- Do not claim a step is done unless a tool result confirms it.\n"
    "- Do not approve, schedule, publish, or change campaign status from chat.\n"
    "- Keep guidance aligned with workflow_state; human actions stay in the product UI."
)

_AGENT_CHAT_CAMPAIGN_AWARE_COPYWRITER_RULES = (
    "Campaign-aware copywriter (revision):\n"
    "- Keep a consistent tone and style across the campaign.\n"
    "- Align copy with workflow_state and the campaign revision context block.\n"
    "- Use the campaign key_message; do not dilute or contradict it.\n"
    "- Do not change the offer unless the user explicitly asks.\n"
    "- Do not invent facts, discounts, dates, or guarantees not supported by context.\n"
    "- Prefer approved_assets_examples as style references when revising drafts."
)


def agent_chat_workflow_context_from_payload(
    input_payload: dict[str, Any],
) -> dict[str, Any] | None:
    raw = input_payload.get("agent_chat")
    if not isinstance(raw, dict) or not raw.get("campaign_id"):
        return None
    return raw


def workflow_state_guidance(
    workflow_state: str,
    *,
    plan_draft_tools: bool = False,
    generate_assets_tools: bool = False,
    revision_tools: bool = False,
) -> str:
    match workflow_state:
        case CampaignWorkflowState.READY_FOR_REVIEW.value:
            if revision_tools:
                return (
                    "Workflow is ready_for_review: improve draft assets via "
                    "content_asset.create_revision when asked; human approval stays in "
                    "Review Queue (/review)."
                )
            return (
                "Workflow is ready_for_review: direct the user to the Review Queue "
                "(/review) to approve or archive pending assets."
            )
        case CampaignWorkflowState.PLAN_READY.value:
            if generate_assets_tools:
                return (
                    "Workflow is plan_ready: when the user asks to materialize the plan, "
                    "call campaign_plan_draft.generate_assets with campaign_id and draft_id."
                )
            return (
                "Workflow is plan_ready: suggest Generate Assets from the campaign "
                "plan draft in the campaign UI (human-initiated)."
            )
        case CampaignWorkflowState.APPROVED_FOR_PUBLICATION.value:
            return (
                "Workflow is approved_for_publication: suggest Schedule Publication "
                "via Channels / publication calendar (human-initiated)."
            )
        case CampaignWorkflowState.PLANNING.value:
            if plan_draft_tools:
                return (
                    "Workflow is planning: when the user asks for a campaign plan, call "
                    "campaign_plan_draft.create for the selected campaign_id with a "
                    "structured plan_payload."
                )
            return (
                "Workflow is planning: suggest creating a campaign plan draft when "
                "appropriate (human-initiated in UI; not via chat)."
            )
        case CampaignWorkflowState.ASSETS_GENERATED.value:
            if revision_tools:
                return (
                    "Workflow is assets_generated: when the user asks to improve content, "
                    "list draft campaign assets (campaign_asset.list), read each with "
                    "content_asset.get, then call content_asset.create_revision with the "
                    f"rewritten body (max {AGENT_CHAT_CAMPAIGN_REVISION_MAX_ASSETS} assets)."
                )
            return (
                "Workflow is assets_generated: suggest reviewing drafts and moving "
                "assets toward human review."
            )
        case CampaignWorkflowState.CONTENT_IN_REVISION.value:
            if revision_tools:
                return (
                    "Workflow is content_in_revision: use content_asset.create_revision "
                    "to improve draft or approved-source revisions; no approve from chat."
                )
            return (
                "Workflow is content_in_revision: suggest finishing revisions before "
                "review or approval."
            )
        case CampaignWorkflowState.COMPLETED.value:
            return "Workflow is completed: suggest monitoring outcomes or starting a new cycle."
        case _:
            return "Use next_recommended_action as the primary guidance for the user."


def revision_context_from_workflow(workflow_context: dict[str, Any]) -> dict[str, Any] | None:
    raw = workflow_context.get("revision_context")
    return raw if isinstance(raw, dict) else None


def scenario_context_from_workflow(workflow_context: dict[str, Any]) -> dict[str, Any] | None:
    raw = workflow_context.get("scenario_context")
    return raw if isinstance(raw, dict) else None


def subagent_routing_from_workflow(workflow_context: dict[str, Any]) -> dict[str, Any] | None:
    raw = workflow_context.get("subagent_routing")
    return raw if isinstance(raw, dict) else None


def selected_subagent_from_workflow(
    workflow_context: dict[str, Any],
) -> MarketerSubAgentType | None:
    routing = subagent_routing_from_workflow(workflow_context)
    if routing is None:
        return None
    raw = routing.get("selected_subagent")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return MarketerSubAgentType(raw.strip())
    except ValueError:
        return None


def _workflow_context_for_display(workflow_context: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in workflow_context.items()
        if key not in {"revision_context", "scenario_context", "subagent_routing"}
    }


def build_agent_chat_workflow_system_content(
    workflow_context: dict[str, Any],
    *,
    plan_draft_tools: bool = False,
    generate_assets_tools: bool = False,
    revision_tools: bool = False,
    agent_type: AgentType | None = None,
) -> str:
    state = str(workflow_context.get("workflow_state", ""))
    guidance = workflow_state_guidance(
        state,
        plan_draft_tools=plan_draft_tools,
        generate_assets_tools=generate_assets_tools,
        revision_tools=revision_tools,
    )
    if revision_tools:
        rules = _AGENT_CHAT_REVISION_RULES
    elif generate_assets_tools:
        rules = _AGENT_CHAT_GENERATE_ASSETS_RULES
    elif plan_draft_tools:
        rules = _AGENT_CHAT_PLAN_DRAFT_RULES
    else:
        rules = _AGENT_CHAT_ADVISOR_RULES

    sections = [rules]
    if revision_tools and agent_type == AgentType.COPYWRITER:
        sections.append(_AGENT_CHAT_CAMPAIGN_AWARE_COPYWRITER_RULES)

    scenario_context = scenario_context_from_workflow(workflow_context)
    if (
        agent_type == AgentType.ORCHESTRATOR
        and scenario_context is not None
        and scenario_context.get("scenario_detected")
    ):
        sections.append(_AGENT_CHAT_ORCHESTRATOR_SCENARIO_RULES)

    revision_context = revision_context_from_workflow(workflow_context)
    workflow_for_block = _workflow_context_for_display(workflow_context)
    sections.append(guidance)
    sections.append(format_context_block("Campaign workflow context", workflow_for_block))
    if revision_tools and revision_context is not None:
        sections.append(format_context_block("Campaign revision context", revision_context))
    if agent_type == AgentType.ORCHESTRATOR and scenario_context is not None:
        sections.append(format_context_block("Marketing scenario context", scenario_context))

    if agent_type == AgentType.ORCHESTRATOR:
        selected_subagent = selected_subagent_from_workflow(workflow_context)
        if selected_subagent is not None:
            from app.agents.marketer.registry import get_subagent, get_subagent_prompt

            profile = get_subagent(selected_subagent)
            sections.append(get_subagent_prompt(selected_subagent))
            sections.append(
                format_context_block(
                    "Marketer sub-agent routing",
                    {
                        "selected_subagent": selected_subagent.value,
                        "persona_name": profile.name,
                        "responsibilities": list(profile.responsibilities),
                        "allowed_tools": sorted(profile.allowed_tools),
                    },
                ),
            )

    return "\n\n".join(sections)


def supports_agent_chat_workflow(agent_type: AgentType, *, revision_tools: bool = False) -> bool:
    if agent_type in _AGENT_CHAT_ADVISOR_TYPES:
        return True
    return revision_tools and agent_type == AgentType.COPYWRITER
