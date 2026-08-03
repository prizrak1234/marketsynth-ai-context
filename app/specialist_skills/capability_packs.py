"""SpecialistCapabilityPack definitions — allowlists per role."""

from __future__ import annotations

from app.schemas.contracts import SpecialistCapabilityPack, SpecialistSkillCode

_PACKS: dict[str, SpecialistCapabilityPack] = {
    "content_specialist": SpecialistCapabilityPack(
        specialist_role="content_specialist",
        version="1.0",
        allowed_skills=[
            SpecialistSkillCode.CONTENT_TELEGRAM_POST,
            SpecialistSkillCode.CONTENT_SOCIAL_POST,
            SpecialistSkillCode.CONTENT_YOUTUBE_SCRIPT,
            SpecialistSkillCode.CONTENT_CONTENT_PLAN,
        ],
        default_skill=SpecialistSkillCode.CONTENT_TELEGRAM_POST,
        knowledge_scopes=[
            "constitutional",
            "content_methodology",
            "content_templates",
            "owner_brand",
            "project_brief",
            "approved_examples",
        ],
        tool_profile=["knowledge_search"],
        forbidden_tools=[
            "shell",
            "filesystem_write",
            "git_mutate",
            "deploy",
            "business_verdict_approve",
            "publish",
        ],
        output_policy="draft_only_owner_review",
        approval_policy="owner_review_before_final",
        quality_profile=["no_fake_facts", "platform_fit", "brand_voice"],
        locale_policy=["ru", "en"],
    ),
    "content_planner": SpecialistCapabilityPack(
        specialist_role="content_planner",
        version="1.0",
        allowed_skills=[SpecialistSkillCode.CONTENT_CONTENT_PLAN],
        default_skill=SpecialistSkillCode.CONTENT_CONTENT_PLAN,
        knowledge_scopes=[
            "constitutional",
            "content_methodology",
            "content_plan_template",
            "project_brief",
        ],
        tool_profile=["knowledge_search"],
        forbidden_tools=["shell", "deploy", "publish", "business_verdict_approve"],
        output_policy="draft_only_owner_review",
        approval_policy="owner_review_before_final",
        quality_profile=["no_fake_facts", "plan_completeness", "brand_voice"],
        locale_policy=["ru", "en"],
    ),
    "visual_specialist": SpecialistCapabilityPack(
        specialist_role="visual_specialist",
        version="1.0",
        allowed_skills=[SpecialistSkillCode.DESIGN_IMAGE_GENERATION],
        default_skill=SpecialistSkillCode.DESIGN_IMAGE_GENERATION,
        knowledge_scopes=["constitutional", "content_quality"],
        tool_profile=["image_generation"],
        forbidden_tools=[
            "shell",
            "deploy",
            "publish",
            "business_verdict_approve",
            "campaign_create",
            "budget_action",
        ],
        output_policy="generate_image_only_no_publication",
        approval_policy="explicit_user_request",
        quality_profile=["safety", "no_publication", "owner_isolation"],
        locale_policy=["ru", "en"],
    ),
    "researcher": SpecialistCapabilityPack(
        specialist_role="researcher",
        version="1.0",
        allowed_skills=[
            SpecialistSkillCode.RESEARCH_MARKET_OVERVIEW,
            SpecialistSkillCode.RESEARCH_COMPETITOR_ANALYSIS,
            SpecialistSkillCode.RESEARCH_AUDIENCE_SEGMENTATION,
        ],
        default_skill=SpecialistSkillCode.RESEARCH_MARKET_OVERVIEW,
        knowledge_scopes=[
            "constitutional",
            "research_methodology",
            "research_templates",
            "project_sources",
            "project_evidence",
            "approved_examples",
        ],
        tool_profile=["knowledge_search", "source_lookup"],
        forbidden_tools=[
            "shell",
            "deploy",
            "publish",
            "business_verdict_approve",
            "web_scrape_unreviewed",
        ],
        output_policy="draft_with_visible_citations",
        approval_policy="owner_review_before_final",
        quality_profile=[
            "citation_required",
            "no_fake_facts",
            "insufficient_data_when_gap",
        ],
        locale_policy=["ru", "en"],
    ),
    "programmer": SpecialistCapabilityPack(
        specialist_role="programmer",
        version="1.0",
        allowed_skills=[
            SpecialistSkillCode.PROGRAMMER_TELEGRAM_BOT_SPEC,
            SpecialistSkillCode.PROGRAMMER_WEBSITE_SPEC,
            SpecialistSkillCode.PROGRAMMER_AUTOMATION_SPEC,
        ],
        default_skill=SpecialistSkillCode.PROGRAMMER_TELEGRAM_BOT_SPEC,
        knowledge_scopes=[
            "constitutional",
            "programmer_methodology",
            "telegram_bot_spec_template",
            "website_spec_template",
            "automation_spec_template",
            "project_brief",
        ],
        tool_profile=["knowledge_search"],
        forbidden_tools=[
            "shell",
            "filesystem_write",
            "git_mutate",
            "deploy",
            "publish",
            "business_verdict_approve",
        ],
        output_policy="specification_draft_only",
        approval_policy="owner_review_before_final",
        quality_profile=["spec_completeness", "no_deploy", "no_fake_integrations"],
        locale_policy=["ru", "en"],
    ),
    "strategist": SpecialistCapabilityPack(
        specialist_role="strategist",
        version="1.0",
        allowed_skills=[
            SpecialistSkillCode.STRATEGY_POSITIONING,
            SpecialistSkillCode.STRATEGY_OFFER_DESIGN,
            SpecialistSkillCode.STRATEGY_CHANNEL_SELECTION,
        ],
        default_skill=SpecialistSkillCode.STRATEGY_POSITIONING,
        knowledge_scopes=[
            "constitutional",
            "strategy_methodology",
            "offer_methodology",
            "project_brief",
            "project_evidence",
        ],
        tool_profile=["knowledge_search", "source_lookup"],
        forbidden_tools=["shell", "deploy", "publish", "business_verdict_approve"],
        output_policy="draft_with_visible_citations_when_factual",
        approval_policy="owner_review_before_final",
        quality_profile=["citation_required", "no_fake_facts", "domain_eligibility"],
        locale_policy=["ru", "en"],
    ),
}


def list_capability_packs() -> list[SpecialistCapabilityPack]:
    return list(_PACKS.values())


def get_capability_pack(specialist_role: str) -> SpecialistCapabilityPack | None:
    return _PACKS.get(specialist_role)


def skill_allowed_for_specialist(
    specialist_role: str,
    skill_code: SpecialistSkillCode,
) -> bool:
    pack = get_capability_pack(specialist_role)
    if pack is None:
        return False
    return skill_code in pack.allowed_skills
