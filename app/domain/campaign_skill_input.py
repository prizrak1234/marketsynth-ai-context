"""Build skill run inputs from campaign state (Phase AI.239)."""

from __future__ import annotations

from typing import Any

from app.db.models.campaign import CampaignTable
from app.schemas.contracts import CampaignActionType, CampaignBriefFields, MarketingSkillType


def build_campaign_skill_input(
    campaign: CampaignTable,
    skill_type: MarketingSkillType,
    *,
    brief: CampaignBriefFields | None = None,
    create_tool_call: bool = False,
) -> dict[str, Any]:
    metadata = campaign.campaign_metadata or {}
    intent = metadata.get("source_business_intent")
    intent_data = intent if isinstance(intent, dict) else {}

    payload: dict[str, Any] = {
        "campaign_id": str(campaign.id),
        "source": "campaign_control_center",
        "industry": (brief.industry if brief else None) or intent_data.get("industry"),
        "goal": (brief.goal if brief else None) or intent_data.get("goal") or campaign.goal,
        "geography": brief.geography if brief else intent_data.get("geography"),
        "target_audience": (brief.target_audience if brief else None)
        or intent_data.get("target_audience")
        or campaign.name,
        "offer": (brief.offer if brief else None) or intent_data.get("offer") or campaign.goal,
        "segment_name": (brief.target_audience if brief else None) or campaign.name,
    }

    if skill_type == MarketingSkillType.WORDSTAT_RESEARCH:
        payload["query"] = payload.get("offer") or payload.get("industry") or campaign.goal
        payload["create_tool_call"] = create_tool_call
    elif skill_type == MarketingSkillType.METRICA_ANALYSIS:
        payload["create_tool_call"] = create_tool_call
        payload["natural_language"] = "traffic and device breakdown"
    elif skill_type == MarketingSkillType.VISUAL_REPORT:
        payload["create_tool_call"] = create_tool_call
        payload["prompt"] = f"Marketing visual for {payload.get('industry') or 'campaign'}: {payload.get('offer')}"

    return payload


SKILL_ACTION_TO_TYPE: dict[str, MarketingSkillType] = {
    "run_segment_research": MarketingSkillType.SEGMENT_RESEARCH,
    "run_meaning_unpacking": MarketingSkillType.MEANING_UNPACKING,
    "run_offer_packaging": MarketingSkillType.OFFER_PACKAGING,
    "run_offer_justification": MarketingSkillType.OFFER_JUSTIFICATION,
    "run_wordstat_research": MarketingSkillType.WORDSTAT_RESEARCH,
    "run_metrica_analysis": MarketingSkillType.METRICA_ANALYSIS,
    "run_visual_report": MarketingSkillType.VISUAL_REPORT,
}

SKILL_TYPE_TO_ACTION: dict[MarketingSkillType, CampaignActionType] = {
    skill_type: CampaignActionType(action)
    for action, skill_type in SKILL_ACTION_TO_TYPE.items()
}
