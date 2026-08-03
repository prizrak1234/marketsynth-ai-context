"""Campaign workflow step progress inference (Phase AI.262)."""

from __future__ import annotations

from app.marketing.workflows.registry import get_workflow_template
from app.schemas.contracts import (
    CampaignActionType,
    CampaignWorkflowRunStatus,
    CampaignWorkflowStep,
    CampaignWorkflowStepStatus,
    CampaignWorkflowStepView,
    CampaignWorkflowTemplate,
    MarketingSkillRunStatus,
    MarketingSkillType,
)

_SKILL_ACTION_MAP: dict[CampaignActionType, MarketingSkillType] = {
    CampaignActionType.RUN_SEGMENT_RESEARCH: MarketingSkillType.SEGMENT_RESEARCH,
    CampaignActionType.RUN_MEANING_UNPACKING: MarketingSkillType.MEANING_UNPACKING,
    CampaignActionType.RUN_OFFER_PACKAGING: MarketingSkillType.OFFER_PACKAGING,
    CampaignActionType.RUN_OFFER_JUSTIFICATION: MarketingSkillType.OFFER_JUSTIFICATION,
    CampaignActionType.RUN_WORDSTAT_RESEARCH: MarketingSkillType.WORDSTAT_RESEARCH,
    CampaignActionType.RUN_METRICA_ANALYSIS: MarketingSkillType.METRICA_ANALYSIS,
    CampaignActionType.RUN_VISUAL_REPORT: MarketingSkillType.VISUAL_REPORT,
}

_SKILL_CONTEXT_KEYS: dict[MarketingSkillType, str] = {
    MarketingSkillType.SEGMENT_RESEARCH: "segment_summary",
    MarketingSkillType.MEANING_UNPACKING: "offer_summary",
    MarketingSkillType.OFFER_PACKAGING: "offer_summary",
    MarketingSkillType.OFFER_JUSTIFICATION: "offer_summary",
    MarketingSkillType.WORDSTAT_RESEARCH: "demand_summary",
    MarketingSkillType.METRICA_ANALYSIS: "analytics_summary",
    MarketingSkillType.VISUAL_REPORT: "offer_summary",
}


class CampaignWorkflowStepMapper:
    """Maps workflow steps to existing actions/skills — recommendation only."""

    @staticmethod
    def skill_type_for_action(action_type: CampaignActionType) -> MarketingSkillType | None:
        return _SKILL_ACTION_MAP.get(action_type)

    @staticmethod
    def is_step_complete(
        step: CampaignWorkflowStep,
        *,
        completed_skill_types: set[MarketingSkillType],
        skill_context_keys: set[str],
        has_content_asset: bool,
        has_media_brief: bool,
        has_publication_package: bool,
        step_results: dict,
    ) -> bool:
        if step.step_id in step_results:
            return bool(step_results.get(step.step_id))

        skill_type = step.recommended_skill_type
        if skill_type is None and step.recommended_action_type is not None:
            skill_type = CampaignWorkflowStepMapper.skill_type_for_action(
                step.recommended_action_type,
            )

        if skill_type is not None:
            context_key = _SKILL_CONTEXT_KEYS.get(skill_type)
            if skill_type in completed_skill_types:
                return True
            if context_key and context_key in skill_context_keys:
                return True

        action = step.recommended_action_type
        if action == CampaignActionType.CREATE_CONTENT_ASSET:
            return has_content_asset
        if action == CampaignActionType.CREATE_MEDIA_BRIEF:
            return has_media_brief
        if action == CampaignActionType.CREATE_PUBLICATION_PACKAGE:
            return has_publication_package
        return False

    @staticmethod
    def build_step_views(
        template: CampaignWorkflowTemplate,
        *,
        current_step_index: int,
        run_status: CampaignWorkflowRunStatus,
        step_results: dict,
        completed_skill_types: set[MarketingSkillType],
        skill_context_keys: set[str],
        has_content_asset: bool,
        has_media_brief: bool,
        has_publication_package: bool,
    ) -> list[CampaignWorkflowStepView]:
        views: list[CampaignWorkflowStepView] = []
        first_incomplete: int | None = None

        for index, step in enumerate(template.steps):
            completed = CampaignWorkflowStepMapper.is_step_complete(
                step,
                completed_skill_types=completed_skill_types,
                skill_context_keys=skill_context_keys,
                has_content_asset=has_content_asset,
                has_media_brief=has_media_brief,
                has_publication_package=has_publication_package,
                step_results=step_results,
            )
            if not completed and first_incomplete is None:
                first_incomplete = index

            if completed:
                status = CampaignWorkflowStepStatus.COMPLETED
            elif run_status == CampaignWorkflowRunStatus.COMPLETED:
                status = CampaignWorkflowStepStatus.COMPLETED if index <= current_step_index else CampaignWorkflowStepStatus.PENDING
            elif first_incomplete is not None and index == first_incomplete:
                status = CampaignWorkflowStepStatus.CURRENT
            elif index < current_step_index:
                status = CampaignWorkflowStepStatus.COMPLETED
            else:
                status = CampaignWorkflowStepStatus.PENDING

            views.append(
                CampaignWorkflowStepView(
                    step_index=index,
                    step_id=step.step_id,
                    label=step.label,
                    safe_description=step.safe_description,
                    status=status,
                    recommended_action_type=step.recommended_action_type,
                    recommended_skill_type=step.recommended_skill_type,
                    recommended_tool_type=step.recommended_tool_type,
                ),
            )

        return views

    @staticmethod
    def progress_percent(steps: list[CampaignWorkflowStepView]) -> int:
        if not steps:
            return 0
        completed = sum(
            1 for step in steps if step.status == CampaignWorkflowStepStatus.COMPLETED
        )
        return int(round(completed * 100 / len(steps)))


def completed_skill_types_from_runs(skill_runs: list) -> set[MarketingSkillType]:
    completed: set[MarketingSkillType] = set()
    for row in skill_runs:
        if getattr(row, "status", None) != MarketingSkillRunStatus.SUCCEEDED:
            continue
        try:
            completed.add(MarketingSkillType(row.skill_type))
        except ValueError:
            continue
    return completed
