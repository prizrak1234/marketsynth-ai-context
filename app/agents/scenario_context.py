"""Marketing scenario context for orchestrator agent chat (Phase AI.9)."""

from __future__ import annotations

from app.agents.scenarios.contracts import MarketingScenarioType
from app.schemas.contracts import (
    CampaignWorkflowRecommendedAction,
    CampaignWorkflowState,
)

_MAX_RECOMMENDED_STEPS = 5


def build_marketing_scenario_context(
    *,
    scenario_type: MarketingScenarioType | None,
    workflow_state: str,
    next_recommended_action: str = "",
    pending_review_assets: int = 0,
) -> dict[str, object]:
    steps = build_recommended_next_steps(
        scenario_type=scenario_type,
        workflow_state=workflow_state,
        next_recommended_action=next_recommended_action,
        pending_review_assets=pending_review_assets,
    )
    return {
        "scenario_type": scenario_type.value if scenario_type is not None else None,
        "scenario_detected": scenario_type is not None,
        "workflow_state": workflow_state,
        "next_recommended_action": next_recommended_action,
        "pending_review_assets": pending_review_assets,
        "recommended_next_steps": steps,
    }


def build_recommended_next_steps(
    *,
    scenario_type: MarketingScenarioType | None,
    workflow_state: str,
    next_recommended_action: str = "",
    pending_review_assets: int = 0,
) -> list[str]:
    if scenario_type is not None:
        scenario_steps = _steps_for_scenario(
            scenario_type,
            workflow_state=workflow_state,
            pending_review_assets=pending_review_assets,
        )
        if scenario_steps:
            return scenario_steps[:_MAX_RECOMMENDED_STEPS]

    return _steps_for_workflow_fallback(
        workflow_state=workflow_state,
        next_recommended_action=next_recommended_action,
        pending_review_assets=pending_review_assets,
    )[:_MAX_RECOMMENDED_STEPS]


def _steps_for_scenario(
    scenario_type: MarketingScenarioType,
    *,
    workflow_state: str,
    pending_review_assets: int,
) -> list[str]:
    match scenario_type:
        case MarketingScenarioType.TELEGRAM_CONTENT_MONTH:
            return _telegram_month_steps(workflow_state, pending_review_assets=pending_review_assets)
        case MarketingScenarioType.PRODUCT_ANNOUNCEMENT:
            return _product_announcement_steps(workflow_state, pending_review_assets=pending_review_assets)
        case MarketingScenarioType.LEAD_MAGNET:
            return _lead_magnet_steps(workflow_state, pending_review_assets=pending_review_assets)
        case MarketingScenarioType.CAMPAIGN_REVIVAL:
            return _campaign_revival_steps(workflow_state, pending_review_assets=pending_review_assets)
        case MarketingScenarioType.CONTENT_LAUNCH:
            return _content_launch_steps(workflow_state, pending_review_assets=pending_review_assets)
        case _:
            return []


def _telegram_month_steps(workflow_state: str, *, pending_review_assets: int) -> list[str]:
    match workflow_state:
        case CampaignWorkflowState.PLANNING.value:
            return [
                "Clarify monthly Telegram goals and audience segments.",
                "Create a campaign plan draft with weekly content_items (human or gated chat tool).",
                "Generate draft assets from the plan when the plan is ready.",
            ]
        case CampaignWorkflowState.PLAN_READY.value:
            return [
                "Generate draft assets from the approved plan draft.",
                "Review each Telegram post draft in Review Queue.",
            ]
        case CampaignWorkflowState.READY_FOR_REVIEW.value:
            return _review_approve_schedule_steps(pending_review_assets)
        case CampaignWorkflowState.APPROVED_FOR_PUBLICATION.value:
            return _schedule_monitor_steps()
        case _:
            return _content_launch_steps(workflow_state, pending_review_assets=pending_review_assets)


def _product_announcement_steps(workflow_state: str, *, pending_review_assets: int) -> list[str]:
    match workflow_state:
        case CampaignWorkflowState.PLANNING.value:
            return [
                "Align launch timeline, offer, and primary channel in the campaign plan.",
                "Create a plan draft focused on announcement beats (teaser → launch → follow-up).",
            ]
        case CampaignWorkflowState.ASSETS_GENERATED.value | CampaignWorkflowState.CONTENT_IN_REVISION.value:
            return [
                "Polish announcement copy for clarity and urgency (revision tools if enabled).",
                "Move assets to Review Queue for human approval.",
            ]
        case CampaignWorkflowState.READY_FOR_REVIEW.value:
            return _review_approve_schedule_steps(pending_review_assets)
        case _:
            return _content_launch_steps(workflow_state, pending_review_assets=pending_review_assets)


def _lead_magnet_steps(workflow_state: str, *, pending_review_assets: int) -> list[str]:
    match workflow_state:
        case CampaignWorkflowState.PLANNING.value:
            return [
                "Define the lead magnet offer and conversion goal.",
                "Plan landing/post sequence in a campaign plan draft.",
            ]
        case CampaignWorkflowState.PLAN_READY.value:
            return [
                "Generate draft assets for the magnet and supporting posts.",
                "Review copy for a clear CTA and deliverable promise.",
            ]
        case CampaignWorkflowState.READY_FOR_REVIEW.value:
            return _review_approve_schedule_steps(pending_review_assets)
        case _:
            return _content_launch_steps(workflow_state, pending_review_assets=pending_review_assets)


def _campaign_revival_steps(workflow_state: str, *, pending_review_assets: int) -> list[str]:
    match workflow_state:
        case CampaignWorkflowState.COMPLETED.value:
            return [
                "Review campaign overview counts and past publication outcomes.",
                "Decide whether to revise existing assets or create a fresh plan draft.",
                "Re-open Review Queue for any refreshed drafts before scheduling again.",
            ]
        case _:
            return [
                "Audit current workflow state with marketing_campaign.workflow.",
                "Refresh underperforming drafts or approve pending items in Review Queue.",
                "Schedule the next publication window when assets are approved.",
            ]


def _content_launch_steps(workflow_state: str, *, pending_review_assets: int) -> list[str]:
    match workflow_state:
        case CampaignWorkflowState.PLANNING.value:
            return [
                "Confirm campaign goal and key message in the plan draft.",
                "Create the campaign plan draft when messaging is agreed.",
            ]
        case CampaignWorkflowState.PLAN_READY.value:
            return [
                "Generate draft content assets from the plan draft.",
            ]
        case CampaignWorkflowState.ASSETS_GENERATED.value | CampaignWorkflowState.CONTENT_IN_REVISION.value:
            return [
                "Review draft assets and request revisions where needed.",
                "Submit strong drafts to Review Queue for human approval.",
            ]
        case CampaignWorkflowState.READY_FOR_REVIEW.value:
            return _review_approve_schedule_steps(pending_review_assets)
        case CampaignWorkflowState.APPROVED_FOR_PUBLICATION.value:
            return _schedule_monitor_steps()
        case CampaignWorkflowState.COMPLETED.value:
            return [
                "Review publication outcomes in the calendar overview.",
                "Start a revival cycle or a new campaign if goals were met.",
            ]
        case _:
            return []


def _steps_for_workflow_fallback(
    *,
    workflow_state: str,
    next_recommended_action: str,
    pending_review_assets: int,
) -> list[str]:
    match workflow_state:
        case CampaignWorkflowState.PLANNING.value:
            return [
                "Create or refine the campaign plan draft.",
                "Confirm target audience and key message before generating assets.",
            ]
        case CampaignWorkflowState.PLAN_READY.value:
            return [
                "Generate draft assets from the latest plan draft.",
            ]
        case CampaignWorkflowState.ASSETS_GENERATED.value | CampaignWorkflowState.CONTENT_IN_REVISION.value:
            return [
                "Review draft assets and improve weak pieces.",
                "Send ready drafts to Review Queue for human approval.",
            ]
        case CampaignWorkflowState.READY_FOR_REVIEW.value:
            return _review_approve_schedule_steps(pending_review_assets)
        case CampaignWorkflowState.APPROVED_FOR_PUBLICATION.value:
            return _schedule_monitor_steps()
        case CampaignWorkflowState.COMPLETED.value:
            return [
                "Review results and decide on the next campaign cycle.",
            ]
        case _:
            action = next_recommended_action.strip()
            if action and action != CampaignWorkflowRecommendedAction.NONE.value:
                return [f"Follow workflow recommendation: {action} (human-initiated in UI)."]
            return [
                "Read marketing_campaign.workflow and marketing_campaign.overview for facts.",
                "Suggest one safe human next step aligned with the campaign state.",
            ]


def _review_approve_schedule_steps(pending_review_assets: int) -> list[str]:
    count_label = str(pending_review_assets) if pending_review_assets > 0 else "pending"
    return [
        f"Review {count_label} draft asset(s) in Review Queue (/review).",
        "Approve assets in the UI when copy meets brand and compliance checks.",
        "Schedule approved assets in the publication calendar (human-initiated).",
    ]


def _schedule_monitor_steps() -> list[str]:
    return [
        "Schedule approved assets in the publication calendar (human-initiated).",
        "Monitor upcoming jobs via publication_calendar.list when tool access is available.",
    ]
