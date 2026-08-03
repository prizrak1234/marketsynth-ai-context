"""Campaign workflow recommendation engine v1 (Phase AI.259)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.marketing.workflows.registry import get_workflow_template, list_workflow_templates
from app.schemas.contracts import (
    BusinessIntent,
    CampaignBriefFields,
    CampaignSkillContext,
    CampaignSupervisorCategory,
    CampaignSupervisorFinding,
    CampaignSupervisorSeverity,
    CampaignWorkflowSuggestion,
    MarketingSkillType,
)

_LEAD_GOALS = frozenset({"lead_generation", "leads", "lead_gen"})
_CONTENT_GAP_CATEGORIES = frozenset(
    {
        CampaignSupervisorCategory.CONTENT,
        CampaignSupervisorCategory.MEDIA,
        CampaignSupervisorCategory.PUBLISHING,
    }
)


@dataclass(frozen=True, slots=True)
class CampaignWorkflowRecommendationInput:
    scenario_id: str | None = None
    intent: BusinessIntent | None = None
    brief: CampaignBriefFields | None = None
    skill_context: CampaignSkillContext | None = None
    completed_skill_types: set[MarketingSkillType] = field(default_factory=set)
    supervisor_findings: list[CampaignSupervisorFinding] = field(default_factory=list)
    supervisor_missing_inputs: list[str] = field(default_factory=list)
    has_content_asset: bool = False
    has_media_brief: bool = False
    has_publication_package: bool = False
    active_template_ids: set[str] = field(default_factory=set)


def _template_label(template_id: str) -> str:
    template = get_workflow_template(template_id)
    return template.name if template is not None else template_id


def _has_summary(context: CampaignSkillContext | None, key: str) -> bool:
    if context is None:
        return False
    return getattr(context, key, None) is not None


def _scenario_matches(template_id: str, scenario_id: str | None) -> bool:
    if not scenario_id:
        return False
    template = get_workflow_template(template_id)
    if template is None:
        return False
    if not template.applicable_scenarios:
        return True
    return scenario_id in template.applicable_scenarios


def _is_lead_campaign(data: CampaignWorkflowRecommendationInput) -> bool:
    goal = (data.intent.goal if data.intent else "") or ""
    normalized = goal.lower().replace("-", "_").strip()
    if normalized in _LEAD_GOALS:
        return True
    scenario = (data.scenario_id or "").lower()
    return "lead" in scenario or "lead_gen" in scenario


def build_campaign_workflow_suggestions(
    data: CampaignWorkflowRecommendationInput,
) -> list[CampaignWorkflowSuggestion]:
    suggestions: list[CampaignWorkflowSuggestion] = []
    seen: set[str] = set()

    def add(
        template_id: str,
        *,
        reason: str,
        priority: int,
    ) -> None:
        if template_id in data.active_template_ids or template_id in seen:
            return
        template = get_workflow_template(template_id)
        if template is None:
            return
        seen.add(template_id)
        suggestions.append(
            CampaignWorkflowSuggestion(
                template_id=template_id,
                label=_template_label(template_id),
                reason=reason,
                priority=priority,
                expected_artifacts=list(template.expected_artifacts),
            ),
        )

    brief = data.brief
    has_offer = bool(brief and brief.offer)
    has_audience = bool(brief and brief.target_audience)
    missing_inputs = set(data.supervisor_missing_inputs)
    critical_findings = [
        finding
        for finding in data.supervisor_findings
        if finding.severity == CampaignSupervisorSeverity.CRITICAL
    ]
    content_gaps = any(finding.category in _CONTENT_GAP_CATEGORIES for finding in critical_findings)

    if _is_lead_campaign(data) or _scenario_matches("lead_gen_campaign", data.scenario_id):
        add(
            "lead_gen_campaign",
            reason="Lead-generation scenario — structured research-to-launch checklist.",
            priority=1,
        )

    if not has_offer or "offer" in missing_inputs:
        add(
            "offer_validation",
            reason="Supervisor or brief indicates offer inputs need validation before scaling.",
            priority=2,
        )

    if not _has_summary(data.skill_context, "demand_summary") or "wordstat" in " ".join(
        missing_inputs
    ).lower():
        add(
            "metrica_traffic_diagnostics",
            reason="Demand or traffic diagnostics missing — align Metrica with Wordstat signals.",
            priority=3,
        )

    if content_gaps or (has_offer and not data.has_content_asset):
        add(
            "content_machine",
            reason="Content or publishing gaps detected — run the content production workflow.",
            priority=3,
        )

    if data.has_content_asset and not data.has_media_brief:
        add(
            "visual_content_pack",
            reason="Copy exists but visual/media artifacts are missing.",
            priority=4,
        )

    if has_audience and MarketingSkillType.SEGMENT_RESEARCH not in data.completed_skill_types:
        if not _has_summary(data.skill_context, "segment_summary"):
            add(
                "offer_validation",
                reason="Segment research not reflected in campaign skill context yet.",
                priority=4,
            )

    for finding in data.supervisor_findings:
        title = finding.title.lower()
        if "wordstat" in title or "demand" in title:
            add(
                "metrica_traffic_diagnostics",
                reason=f"Supervisor finding: {finding.title}",
                priority=2,
            )
        if finding.category == CampaignSupervisorCategory.BRIEF:
            add(
                "offer_validation",
                reason=f"Supervisor brief gap: {finding.title}",
                priority=2,
            )

    if not suggestions:
        for template in list_workflow_templates():
            if _scenario_matches(template.id, data.scenario_id):
                add(
                    template.id,
                    reason=f"Default template for scenario {data.scenario_id}.",
                    priority=6,
                )

    suggestions.sort(key=lambda item: (item.priority, item.label))
    return suggestions[:5]
