"""Campaign supervisor rule engine v1 (Phase AI.248)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.marketing.contracts import ContentAssetStatus, PublicationPackageStatus
from app.marketing.media_contracts import MediaBriefStatus
from app.publishing_foundation.contracts import PublicationPackageJobStatus
from app.schemas.contracts import (
    BusinessIntent,
    CampaignActionType,
    CampaignBriefFields,
    CampaignHealthStatus,
    CampaignNextActionType,
    CampaignSkillContext,
    CampaignStatus,
    CampaignSupervisorCategory,
    CampaignSupervisorFinding,
    CampaignSupervisorReport,
    CampaignSupervisorSeverity,
    MarketingSkillRunStatus,
    MarketingSkillType,
    MarketingSpecialistType,
)

_CONTENT_SPECIALISTS = (
    MarketingSpecialistType.COPYWRITER,
    MarketingSpecialistType.SALES_COPYWRITER,
)
_LEAD_GOALS = frozenset({"lead_generation", "leads", "lead_gen"})
_SEVERITY_ORDER = {
    CampaignSupervisorSeverity.CRITICAL: 0,
    CampaignSupervisorSeverity.WARNING: 1,
    CampaignSupervisorSeverity.INFO: 2,
}


@dataclass(frozen=True, slots=True)
class CampaignSupervisorInput:
    campaign_id: UUID
    campaign_status: CampaignStatus
    scenario_id: str | None
    intent: BusinessIntent | None
    brief: CampaignBriefFields | None
    skill_context: CampaignSkillContext | None
    completed_skill_types: set[MarketingSkillType] = field(default_factory=set)
    next_action_type: CampaignNextActionType = CampaignNextActionType.NONE
    health_status: CampaignHealthStatus = CampaignHealthStatus.HEALTHY
    has_copywriter_output: bool = False
    copywriter_output_id: UUID | None = None
    has_content_asset: bool = False
    content_asset_approved: bool = False
    content_asset_id: UUID | None = None
    has_media_brief: bool = False
    media_brief_approved: bool = False
    media_brief_id: UUID | None = None
    has_media_asset: bool = False
    has_publication_package: bool = False
    publication_package_approved: bool = False
    publication_package_id: UUID | None = None
    has_publication_job: bool = False
    publication_job_failed: bool = False
    publication_job_id: UUID | None = None
    has_website_channel: bool = False


def _finding(
    severity: CampaignSupervisorSeverity,
    category: CampaignSupervisorCategory,
    title: str,
    description: str,
    *,
    affected_resource_type: str | None = None,
    affected_resource_id: UUID | None = None,
    recommended_action_type: CampaignActionType | None = None,
    safe_metadata: dict[str, Any] | None = None,
) -> CampaignSupervisorFinding:
    return CampaignSupervisorFinding(
        severity=severity,
        category=category,
        title=title,
        description=description,
        affected_resource_type=affected_resource_type,
        affected_resource_id=affected_resource_id,
        recommended_action_type=recommended_action_type,
        safe_metadata=safe_metadata or {},
    )


def _has_summary(context: CampaignSkillContext | None, key: str) -> bool:
    if context is None:
        return False
    return getattr(context, key, None) is not None


def _is_lead_gen_scenario(intent: BusinessIntent | None, scenario_id: str | None) -> bool:
    if scenario_id and "lead" in scenario_id.lower():
        return True
    if intent is None:
        return False
    goal = (intent.goal or "").lower()
    return goal in _LEAD_GOALS or "lead" in goal


def _metric_is_lead_focused(success_metric: str | None) -> bool:
    if not success_metric:
        return False
    lowered = success_metric.lower()
    return any(token in lowered for token in ("lead", "лид", "заявк", "conversion", "конверс"))


def _health_score(findings: list[CampaignSupervisorFinding]) -> int:
    score = 100
    for item in findings:
        if item.severity == CampaignSupervisorSeverity.CRITICAL:
            score -= 15
        elif item.severity == CampaignSupervisorSeverity.WARNING:
            score -= 8
        else:
            score -= 3
    return max(0, min(100, score))


def build_campaign_supervisor_report(data: CampaignSupervisorInput) -> CampaignSupervisorReport:
    findings: list[CampaignSupervisorFinding] = []
    missing_inputs: list[str] = []
    contradictions: list[str] = []
    risks: list[str] = []
    recommended_actions: list[CampaignActionType] = []

    brief = data.brief
    intent = data.intent
    ctx = data.skill_context

    if brief is None or not (brief.offer or "").strip():
        missing_inputs.append("offer")
        findings.append(
            _finding(
                CampaignSupervisorSeverity.CRITICAL,
                CampaignSupervisorCategory.BRIEF,
                "Missing offer",
                "Campaign brief has no commercial offer — packaging and copy will lack focus.",
                safe_metadata={"field": "offer"},
            ),
        )

    if brief is None or not (brief.target_audience or "").strip():
        missing_inputs.append("target_audience")
        findings.append(
            _finding(
                CampaignSupervisorSeverity.WARNING,
                CampaignSupervisorCategory.BRIEF,
                "Missing target audience",
                "Define who the campaign targets before scaling acquisition.",
                safe_metadata={"field": "target_audience"},
                recommended_action_type=CampaignActionType.RUN_SEGMENT_RESEARCH,
            ),
        )

    if brief is None or not (brief.success_metric or "").strip():
        missing_inputs.append("success_metric")
        findings.append(
            _finding(
                CampaignSupervisorSeverity.WARNING,
                CampaignSupervisorCategory.BRIEF,
                "Missing success metric",
                "Add a measurable success metric to judge campaign outcomes.",
                safe_metadata={"field": "success_metric"},
            ),
        )

    has_offer_signal = bool(brief and brief.offer) or _has_summary(ctx, "offer_summary")
    if has_offer_signal and not _has_summary(ctx, "segment_summary"):
        if MarketingSkillType.SEGMENT_RESEARCH not in data.completed_skill_types:
            findings.append(
                _finding(
                    CampaignSupervisorSeverity.WARNING,
                    CampaignSupervisorCategory.STRATEGY,
                    "Segment research missing before offer work",
                    "Run segment research before offer packaging to avoid weak positioning.",
                    recommended_action_type=CampaignActionType.RUN_SEGMENT_RESEARCH,
                    safe_metadata={"required_skill": "segment_research"},
                ),
            )

    if (
        MarketingSkillType.OFFER_PACKAGING in data.completed_skill_types
        and not _has_summary(ctx, "segment_summary")
        and MarketingSkillType.SEGMENT_RESEARCH not in data.completed_skill_types
    ):
        findings.append(
            _finding(
                CampaignSupervisorSeverity.CRITICAL,
                CampaignSupervisorCategory.OFFER,
                "Offer packaging without segment research",
                "Offer structure exists but segment foundation is missing.",
                recommended_action_type=CampaignActionType.RUN_SEGMENT_RESEARCH,
                safe_metadata={"completed_skill": "offer_packaging"},
            ),
        )

    if _is_lead_gen_scenario(intent, data.scenario_id) and not _has_summary(ctx, "demand_summary"):
        if MarketingSkillType.WORDSTAT_RESEARCH not in data.completed_skill_types:
            findings.append(
                _finding(
                    CampaignSupervisorSeverity.WARNING,
                    CampaignSupervisorCategory.DATA,
                    "Wordstat research recommended for lead generation",
                    "Validate search demand before committing budget to acquisition.",
                    recommended_action_type=CampaignActionType.RUN_WORDSTAT_RESEARCH,
                    safe_metadata={"scenario_goal": intent.goal if intent else None},
                ),
            )

    website_expected = data.has_website_channel or (
        intent is not None and intent.goal in {"lead_generation", "traffic", "promo", "sales"}
    )
    if website_expected and not _has_summary(ctx, "analytics_summary"):
        if MarketingSkillType.METRICA_ANALYSIS not in data.completed_skill_types:
            findings.append(
                _finding(
                    CampaignSupervisorSeverity.INFO,
                    CampaignSupervisorCategory.DATA,
                    "Site analytics review not captured",
                    "Metrica analysis helps spot conversion leaks before scaling spend.",
                    recommended_action_type=CampaignActionType.RUN_METRICA_ANALYSIS,
                    safe_metadata={"has_website_channel": data.has_website_channel},
                ),
            )

    if data.has_copywriter_output and not data.has_content_asset:
        findings.append(
            _finding(
                CampaignSupervisorSeverity.WARNING,
                CampaignSupervisorCategory.CONTENT,
                "Copywriter output without content asset",
                "Approved specialist copy should become a managed content asset.",
                affected_resource_type="marketing_specialist_output",
                affected_resource_id=data.copywriter_output_id,
                recommended_action_type=CampaignActionType.CREATE_CONTENT_ASSET,
            ),
        )

    if data.content_asset_approved and not data.has_publication_package:
        findings.append(
            _finding(
                CampaignSupervisorSeverity.WARNING,
                CampaignSupervisorCategory.CONTENT,
                "Approved asset without publication package",
                "Create a publication package to prepare channel-ready delivery.",
                affected_resource_type="content_asset",
                affected_resource_id=data.content_asset_id,
                recommended_action_type=CampaignActionType.CREATE_PUBLICATION_PACKAGE,
            ),
        )

    if data.content_asset_approved and not data.has_media_brief:
        findings.append(
            _finding(
                CampaignSupervisorSeverity.WARNING,
                CampaignSupervisorCategory.MEDIA,
                "Approved asset without media brief",
                "Media production needs a brief derived from approved content.",
                affected_resource_type="content_asset",
                affected_resource_id=data.content_asset_id,
                recommended_action_type=CampaignActionType.CREATE_MEDIA_BRIEF,
            ),
        )

    if data.media_brief_approved and not data.has_media_asset:
        findings.append(
            _finding(
                CampaignSupervisorSeverity.WARNING,
                CampaignSupervisorCategory.MEDIA,
                "Approved media brief without media asset",
                "Generate or attach media assets after the brief is approved.",
                affected_resource_type="media_brief",
                affected_resource_id=data.media_brief_id,
            ),
        )

    if data.publication_package_approved and not data.has_publication_job:
        findings.append(
            _finding(
                CampaignSupervisorSeverity.WARNING,
                CampaignSupervisorCategory.PUBLISHING,
                "Approved package without publication job",
                "Create a dry-run publication job before scheduling.",
                affected_resource_type="publication_package",
                affected_resource_id=data.publication_package_id,
                recommended_action_type=CampaignActionType.CREATE_PUBLICATION_JOB,
            ),
        )

    if data.publication_job_failed:
        findings.append(
            _finding(
                CampaignSupervisorSeverity.CRITICAL,
                CampaignSupervisorCategory.PUBLISHING,
                "Publication job failed",
                "Review channel configuration and recovery hint before retrying.",
                affected_resource_type="publication_package_job",
                affected_resource_id=data.publication_job_id,
                recommended_action_type=CampaignActionType.DRY_RUN_DISPATCH,
            ),
        )
        risks.append("Publication pipeline blocked by failed job.")

    if _is_lead_gen_scenario(intent, data.scenario_id) and brief and brief.success_metric:
        if not _metric_is_lead_focused(brief.success_metric):
            message = "Lead-generation scenario but success metric is not lead-focused."
            contradictions.append(message)
            findings.append(
                _finding(
                    CampaignSupervisorSeverity.WARNING,
                    CampaignSupervisorCategory.STRATEGY,
                    "Success metric mismatch",
                    message,
                    safe_metadata={
                        "scenario_id": data.scenario_id,
                        "success_metric": brief.success_metric[:120],
                    },
                ),
            )

    if (
        data.campaign_status == CampaignStatus.ACTIVE
        and data.next_action_type == CampaignNextActionType.NONE
        and data.health_status not in {CampaignHealthStatus.COMPLETED, CampaignHealthStatus.FAILED}
    ):
        message = "Campaign is active but control center reports no next action."
        contradictions.append(message)
        findings.append(
            _finding(
                CampaignSupervisorSeverity.INFO,
                CampaignSupervisorCategory.EXECUTION,
                "No recommended next action",
                message,
                safe_metadata={"health_status": data.health_status.value},
            ),
        )

    findings.sort(
        key=lambda item: (
            _SEVERITY_ORDER[item.severity],
            item.category.value,
            item.title,
        ),
    )

    seen_actions: set[CampaignActionType] = set()
    for item in findings:
        if item.recommended_action_type is None:
            continue
        if item.recommended_action_type in seen_actions:
            continue
        seen_actions.add(item.recommended_action_type)
        recommended_actions.append(item.recommended_action_type)

    if any(item.severity == CampaignSupervisorSeverity.CRITICAL for item in findings):
        risks.append("Critical quality gaps may waste budget or delay launch.")

    return CampaignSupervisorReport(
        campaign_id=data.campaign_id,
        health_score=_health_score(findings),
        findings=findings,
        missing_inputs=missing_inputs,
        contradictions=contradictions,
        risks=risks,
        recommended_next_actions=recommended_actions,
    )
