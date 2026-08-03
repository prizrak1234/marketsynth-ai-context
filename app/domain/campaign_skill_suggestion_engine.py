"""Campaign skill suggestion engine v1 (Phase AI.238)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.marketing.skills.registry import get_marketing_skill_registry
from app.schemas.contracts import (
    BusinessIntent,
    CampaignBriefFields,
    CampaignHealthStatus,
    CampaignNextActionType,
    CampaignSkillContext,
    CampaignSkillSuggestion,
    MarketingSkillType,
)


@dataclass(frozen=True, slots=True)
class CampaignSkillSuggestionInput:
    intent: BusinessIntent
    brief: CampaignBriefFields | None = None
    scenario_id: str | None = None
    health_status: CampaignHealthStatus = CampaignHealthStatus.HEALTHY
    next_action_type: CampaignNextActionType = CampaignNextActionType.NONE
    skill_context: CampaignSkillContext | None = None
    completed_skill_types: set[MarketingSkillType] = field(default_factory=set)
    has_plan: bool = False
    has_content_asset: bool = False


def _label_for(skill_type: MarketingSkillType) -> str:
    definition = get_marketing_skill_registry().get(skill_type).definition
    return definition.name


def _has_summary(context: CampaignSkillContext | None, key: str) -> bool:
    if context is None:
        return False
    return getattr(context, key, None) is not None


def build_campaign_skill_suggestions(
    data: CampaignSkillSuggestionInput,
) -> list[CampaignSkillSuggestion]:
    suggestions: list[CampaignSkillSuggestion] = []
    brief = data.brief
    has_audience = bool(brief and brief.target_audience) or bool(data.intent.industry)
    has_offer = bool(brief and brief.offer)
    ctx = data.skill_context
    completed = data.completed_skill_types

    wizard_next = (
        CampaignNextActionType.START_WIZARD
        if not data.has_plan and data.scenario_id
        else data.next_action_type
    )

    def add(
        skill_type: MarketingSkillType,
        *,
        reason: str,
        priority: int,
        expected_output: str,
        related_brief_fields: list[str] | None = None,
        related_next_action: CampaignNextActionType | None = None,
    ) -> None:
        if skill_type in completed:
            return
        suggestions.append(
            CampaignSkillSuggestion(
                skill_type=skill_type,
                reason=reason,
                priority=priority,
                expected_output=expected_output,
                related_brief_fields=related_brief_fields or [],
                related_next_action=related_next_action or wizard_next,
                label=_label_for(skill_type),
            ),
        )

    if has_audience and not _has_summary(ctx, "segment_summary"):
        add(
            MarketingSkillType.SEGMENT_RESEARCH,
            reason="Brief has audience hints but no segment summary on campaign yet.",
            priority=1,
            expected_output="segment_research",
            related_brief_fields=["target_audience", "geography", "industry"],
        )

    if (has_offer or data.intent.industry) and MarketingSkillType.MEANING_UNPACKING not in completed:
        add(
            MarketingSkillType.MEANING_UNPACKING,
            reason="Translate pains and desires into messaging blocks before packaging.",
            priority=2,
            expected_output="meaning_unpacking",
            related_brief_fields=["offer", "target_audience"],
        )

    if has_offer and has_audience and not _has_summary(ctx, "offer_summary"):
        add(
            MarketingSkillType.OFFER_PACKAGING,
            reason="Offer and audience are known — structure a strong commercial offer.",
            priority=3,
            expected_output="offer_packaging",
            related_brief_fields=["offer", "target_audience", "goal"],
        )
        add(
            MarketingSkillType.OFFER_JUSTIFICATION,
            reason="Prepare business justification and CTA after offer structure.",
            priority=4,
            expected_output="offer_justification",
            related_brief_fields=["offer", "success_metric"],
        )

    if (has_offer or data.intent.industry) and not _has_summary(ctx, "demand_summary"):
        add(
            MarketingSkillType.WORDSTAT_RESEARCH,
            reason="Validate search demand before scaling acquisition.",
            priority=2 if data.intent.goal in {"lead_generation", "promo", "sales"} else 5,
            expected_output="wordstat_research",
            related_brief_fields=["offer", "industry", "geography"],
        )

    if data.intent.goal in {"lead_generation", "traffic", "promo", "sales"} and not _has_summary(
        ctx,
        "analytics_summary",
    ):
        add(
            MarketingSkillType.METRICA_ANALYSIS,
            reason="Review site traffic and conversion signals for this goal.",
            priority=3,
            expected_output="metrica_analysis",
            related_brief_fields=["goal", "success_metric"],
        )

    if has_offer and not data.has_content_asset:
        add(
            MarketingSkillType.VISUAL_REPORT,
            reason="Align creative direction before content and media production.",
            priority=5,
            expected_output="visual_report",
            related_brief_fields=["offer", "industry"],
            related_next_action=CampaignNextActionType.CREATE_CONTENT_ASSET
            if data.has_plan
            else None,
        )

    suggestions.sort(key=lambda item: (item.priority, item.skill_type.value))
    return suggestions
