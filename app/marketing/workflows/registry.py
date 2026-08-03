"""Campaign workflow template registry v1 (Phase AI.258)."""

from __future__ import annotations

from app.schemas.contracts import (
    CampaignActionType,
    CampaignWorkflowStep,
    CampaignWorkflowTemplate,
    MarketingSkillType,
    MarketingToolType,
)

WORKFLOW_STEP_ACTION_TYPES: frozenset[CampaignActionType] = frozenset(
    {
        CampaignActionType.RUN_WORDSTAT_RESEARCH,
        CampaignActionType.RUN_SEGMENT_RESEARCH,
        CampaignActionType.RUN_OFFER_PACKAGING,
        CampaignActionType.RUN_MEANING_UNPACKING,
        CampaignActionType.RUN_OFFER_JUSTIFICATION,
        CampaignActionType.RUN_METRICA_ANALYSIS,
        CampaignActionType.RUN_VISUAL_REPORT,
        CampaignActionType.CREATE_CONTENT_ASSET,
        CampaignActionType.CREATE_MEDIA_BRIEF,
        CampaignActionType.CREATE_PUBLICATION_PACKAGE,
    }
)

_LEAD_SCENARIOS = [
    "dental_clinic_lead_gen",
    "local_service_lead_gen",
    "b2b_lead_gen",
]
_CONTENT_SCENARIOS = [
    "content_marketing",
    "social_content_engine",
    "dental_clinic_lead_gen",
]


def _step(
    step_id: str,
    label: str,
    safe_description: str,
    *,
    action: CampaignActionType | None = None,
    skill: MarketingSkillType | None = None,
    tool: MarketingToolType | None = None,
) -> CampaignWorkflowStep:
    return CampaignWorkflowStep(
        step_id=step_id,
        label=label,
        safe_description=safe_description,
        recommended_action_type=action,
        recommended_skill_type=skill,
        recommended_tool_type=tool,
    )


_TEMPLATES: dict[str, CampaignWorkflowTemplate] = {
    "lead_gen_campaign": CampaignWorkflowTemplate(
        id="lead_gen_campaign",
        name="Lead generation campaign",
        goal="Research audience demand, package offer, and prepare launch artifacts for lead capture.",
        applicable_scenarios=_LEAD_SCENARIOS,
        required_brief_fields=["offer", "target_audience", "success_metric"],
        recommended_skills=[
            MarketingSkillType.SEGMENT_RESEARCH,
            MarketingSkillType.WORDSTAT_RESEARCH,
            MarketingSkillType.OFFER_PACKAGING,
        ],
        recommended_tools=[MarketingToolType.WORDSTAT, MarketingToolType.METRICA],
        steps=[
            _step(
                "segment_research",
                "Segment research",
                "Profile the target audience before messaging and offer work.",
                action=CampaignActionType.RUN_SEGMENT_RESEARCH,
                skill=MarketingSkillType.SEGMENT_RESEARCH,
            ),
            _step(
                "wordstat_research",
                "Wordstat demand scan",
                "Validate search demand and keyword themes for the offer.",
                action=CampaignActionType.RUN_WORDSTAT_RESEARCH,
                skill=MarketingSkillType.WORDSTAT_RESEARCH,
                tool=MarketingToolType.WORDSTAT,
            ),
            _step(
                "offer_packaging",
                "Offer packaging",
                "Structure a compelling commercial offer for lead capture.",
                action=CampaignActionType.RUN_OFFER_PACKAGING,
                skill=MarketingSkillType.OFFER_PACKAGING,
            ),
            _step(
                "content_asset",
                "Content asset",
                "Create the primary copy asset for landing or ads.",
                action=CampaignActionType.CREATE_CONTENT_ASSET,
            ),
            _step(
                "publication_package",
                "Publication package",
                "Bundle approved assets for channel launch.",
                action=CampaignActionType.CREATE_PUBLICATION_PACKAGE,
            ),
        ],
        expected_artifacts=[
            "segment_research",
            "wordstat_research",
            "offer_packaging",
            "content_asset",
            "publication_package",
        ],
        out_of_scope=[
            "Auto-run wizard",
            "Background lead sync",
            "Make.com import",
        ],
    ),
    "content_machine": CampaignWorkflowTemplate(
        id="content_machine",
        name="Content machine",
        goal="Turn offer insights into repeatable content and publication packages.",
        applicable_scenarios=_CONTENT_SCENARIOS,
        required_brief_fields=["offer", "target_audience"],
        recommended_skills=[
            MarketingSkillType.MEANING_UNPACKING,
            MarketingSkillType.OFFER_PACKAGING,
        ],
        recommended_tools=[MarketingToolType.WORDSTAT],
        steps=[
            _step(
                "meaning_unpacking",
                "Meaning unpacking",
                "Extract pains, desires, and hooks for messaging.",
                action=CampaignActionType.RUN_MEANING_UNPACKING,
                skill=MarketingSkillType.MEANING_UNPACKING,
            ),
            _step(
                "offer_packaging",
                "Offer packaging",
                "Package the core offer before copy production.",
                action=CampaignActionType.RUN_OFFER_PACKAGING,
                skill=MarketingSkillType.OFFER_PACKAGING,
            ),
            _step(
                "content_asset",
                "Content asset",
                "Produce the primary content asset from approved messaging.",
                action=CampaignActionType.CREATE_CONTENT_ASSET,
            ),
            _step(
                "media_brief",
                "Media brief",
                "Define visual requirements for supporting creatives.",
                action=CampaignActionType.CREATE_MEDIA_BRIEF,
            ),
            _step(
                "publication_package",
                "Publication package",
                "Assemble assets for multi-channel publishing.",
                action=CampaignActionType.CREATE_PUBLICATION_PACKAGE,
            ),
        ],
        expected_artifacts=[
            "meaning_unpacking",
            "offer_packaging",
            "content_asset",
            "media_brief",
            "publication_package",
        ],
        out_of_scope=["Auto-publish", "LLM batch generation"],
    ),
    "offer_validation": CampaignWorkflowTemplate(
        id="offer_validation",
        name="Offer validation",
        goal="Validate segment fit, offer structure, and demand signals before scaling spend.",
        applicable_scenarios=_LEAD_SCENARIOS + ["offer_launch"],
        required_brief_fields=["offer", "target_audience"],
        recommended_skills=[
            MarketingSkillType.SEGMENT_RESEARCH,
            MarketingSkillType.OFFER_PACKAGING,
            MarketingSkillType.OFFER_JUSTIFICATION,
            MarketingSkillType.WORDSTAT_RESEARCH,
        ],
        recommended_tools=[MarketingToolType.WORDSTAT],
        steps=[
            _step(
                "segment_research",
                "Segment research",
                "Confirm who the offer is for and their constraints.",
                action=CampaignActionType.RUN_SEGMENT_RESEARCH,
                skill=MarketingSkillType.SEGMENT_RESEARCH,
            ),
            _step(
                "offer_packaging",
                "Offer packaging",
                "Structure the offer for clarity and conversion.",
                action=CampaignActionType.RUN_OFFER_PACKAGING,
                skill=MarketingSkillType.OFFER_PACKAGING,
            ),
            _step(
                "offer_justification",
                "Offer justification",
                "Build the business case and CTA rationale.",
                action=CampaignActionType.RUN_OFFER_JUSTIFICATION,
                skill=MarketingSkillType.OFFER_JUSTIFICATION,
            ),
            _step(
                "wordstat_research",
                "Wordstat validation",
                "Cross-check demand language against the packaged offer.",
                action=CampaignActionType.RUN_WORDSTAT_RESEARCH,
                skill=MarketingSkillType.WORDSTAT_RESEARCH,
                tool=MarketingToolType.WORDSTAT,
            ),
        ],
        expected_artifacts=[
            "segment_research",
            "offer_packaging",
            "offer_justification",
            "wordstat_research",
        ],
        out_of_scope=["Pricing ML", "Auto budget allocation"],
    ),
    "metrica_traffic_diagnostics": CampaignWorkflowTemplate(
        id="metrica_traffic_diagnostics",
        name="Metrica traffic diagnostics",
        goal="Diagnose site traffic quality and align keyword demand before scaling campaigns.",
        applicable_scenarios=_LEAD_SCENARIOS + ["traffic_audit"],
        required_brief_fields=["success_metric"],
        recommended_skills=[
            MarketingSkillType.METRICA_ANALYSIS,
            MarketingSkillType.WORDSTAT_RESEARCH,
        ],
        recommended_tools=[MarketingToolType.METRICA, MarketingToolType.WORDSTAT],
        steps=[
            _step(
                "metrica_analysis",
                "Metrica analysis",
                "Review traffic sources, goals, and conversion bottlenecks.",
                action=CampaignActionType.RUN_METRICA_ANALYSIS,
                skill=MarketingSkillType.METRICA_ANALYSIS,
                tool=MarketingToolType.METRICA,
            ),
            _step(
                "wordstat_research",
                "Wordstat research",
                "Compare organic/search demand with on-site behavior.",
                action=CampaignActionType.RUN_WORDSTAT_RESEARCH,
                skill=MarketingSkillType.WORDSTAT_RESEARCH,
                tool=MarketingToolType.WORDSTAT,
            ),
        ],
        expected_artifacts=["metrica_analysis", "wordstat_research"],
        out_of_scope=["Auto bid changes", "Live dashboard sync"],
    ),
    "visual_content_pack": CampaignWorkflowTemplate(
        id="visual_content_pack",
        name="Visual content pack",
        goal="Produce visual direction, media brief, and publication-ready creative bundle.",
        applicable_scenarios=_CONTENT_SCENARIOS + ["brand_refresh"],
        required_brief_fields=["offer"],
        recommended_skills=[MarketingSkillType.VISUAL_REPORT],
        recommended_tools=[MarketingToolType.IMAGE_GENERATION],
        steps=[
            _step(
                "visual_report",
                "Visual report",
                "Capture brand/visual direction before media production.",
                action=CampaignActionType.RUN_VISUAL_REPORT,
                skill=MarketingSkillType.VISUAL_REPORT,
                tool=MarketingToolType.IMAGE_GENERATION,
            ),
            _step(
                "media_brief",
                "Media brief",
                "Translate visual direction into production requirements.",
                action=CampaignActionType.CREATE_MEDIA_BRIEF,
            ),
            _step(
                "publication_package",
                "Publication package",
                "Bundle visual and copy assets for launch.",
                action=CampaignActionType.CREATE_PUBLICATION_PACKAGE,
            ),
        ],
        expected_artifacts=["visual_report", "media_brief", "publication_package"],
        out_of_scope=["Auto image generation batch", "Stock library import"],
    ),
}


def list_workflow_templates() -> list[CampaignWorkflowTemplate]:
    return list(_TEMPLATES.values())


def get_workflow_template(template_id: str) -> CampaignWorkflowTemplate | None:
    return _TEMPLATES.get(template_id)
