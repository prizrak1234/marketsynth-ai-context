"""Marketing specialist registry (Phase AI.27; v2 metadata AI.110) — no new execution."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.contracts import MarketingSpecialistType

FORBIDDEN_SPECIALIST_EXECUTION_MARKERS = frozenset(
    {
        "child_run",
        "subagent_execution",
        "tool_execution",
        "auto_delegation",
    },
)

FROZEN_PIPELINE_ORDER: tuple[MarketingSpecialistType, ...] = (
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
    MarketingSpecialistType.CONTENT_PLANNER,
    MarketingSpecialistType.COPYWRITER,
    MarketingSpecialistType.CRITIC,
    MarketingSpecialistType.ANALYST,
)

V2_METADATA_ONLY_SPECIALISTS: frozenset[MarketingSpecialistType] = frozenset()

V2_EXECUTION_ENABLED_SPECIALISTS: frozenset[MarketingSpecialistType] = frozenset(
    {
        MarketingSpecialistType.OFFER_STRATEGIST,
        MarketingSpecialistType.FUNNEL_ARCHITECT,
        MarketingSpecialistType.LEAD_MAGNET_SPECIALIST,
        MarketingSpecialistType.SALES_COPYWRITER,
        MarketingSpecialistType.EMAIL_DM_SPECIALIST,
        MarketingSpecialistType.CRO_SPECIALIST,
        MarketingSpecialistType.SMM_STRATEGIST,
        MarketingSpecialistType.AD_CREATIVE_STRATEGIST,
    },
)

MARKETING_DEPARTMENT_V2_ROLE_COUNT = 14

V2_DEMO_EXECUTION_ORDER: tuple[MarketingSpecialistType, ...] = (
    MarketingSpecialistType.STRATEGIST,
    MarketingSpecialistType.RESEARCHER,
    MarketingSpecialistType.CONTENT_PLANNER,
    MarketingSpecialistType.OFFER_STRATEGIST,
    MarketingSpecialistType.FUNNEL_ARCHITECT,
    MarketingSpecialistType.LEAD_MAGNET_SPECIALIST,
    MarketingSpecialistType.SALES_COPYWRITER,
    MarketingSpecialistType.EMAIL_DM_SPECIALIST,
    MarketingSpecialistType.CRO_SPECIALIST,
    MarketingSpecialistType.SMM_STRATEGIST,
    MarketingSpecialistType.AD_CREATIVE_STRATEGIST,
)


@dataclass(frozen=True)
class MarketingSpecialistProfile:
    specialist_type: MarketingSpecialistType
    name: str
    description: str
    default_objective: str
    default_expected_output: str
    output_type: str
    dependencies: tuple[MarketingSpecialistType, ...]
    structured_data_keys: tuple[str, ...]
    execution_enabled: bool
    out_of_scope: tuple[str, ...] = ()


_REGISTRY: dict[MarketingSpecialistType, MarketingSpecialistProfile] = {
    MarketingSpecialistType.STRATEGIST: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.STRATEGIST,
        name="Strategist",
        description="Positioning, offer, and campaign direction.",
        default_objective="Define positioning and strategic direction",
        default_expected_output="Positioning summary and strategic pillars",
        output_type="strategy",
        dependencies=(),
        structured_data_keys=(
            "positioning",
            "target_audience",
            "key_message",
            "strategic_risks",
            "next_specialists",
        ),
        execution_enabled=True,
    ),
    MarketingSpecialistType.RESEARCHER: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.RESEARCHER,
        name="Researcher",
        description="Audience, market, and brief research.",
        default_objective="Research audience and market context",
        default_expected_output="Audience insights and evidence-backed notes",
        output_type="research",
        dependencies=(MarketingSpecialistType.STRATEGIST,),
        structured_data_keys=(
            "audience_segments",
            "pains",
            "desires",
            "objections",
            "market_assumptions",
            "research_gaps",
        ),
        execution_enabled=True,
    ),
    MarketingSpecialistType.CONTENT_PLANNER: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.CONTENT_PLANNER,
        name="Content Planner",
        description="Editorial calendar and content structure.",
        default_objective="Build a structured content plan",
        default_expected_output="Channel-aware content plan outline",
        output_type="content_plan",
        dependencies=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
        ),
        structured_data_keys=(
            "content_pillars",
            "funnel_stages",
            "post_ideas",
            "publishing_sequence",
            "channel_recommendations",
        ),
        execution_enabled=True,
    ),
    MarketingSpecialistType.COPYWRITER: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.COPYWRITER,
        name="Copywriter",
        description="Drafts and copy variants for channels.",
        default_objective="Prepare channel-ready copy drafts",
        default_expected_output="Copy variants aligned to strategy",
        output_type="content_copy",
        dependencies=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.CONTENT_PLANNER,
        ),
        structured_data_keys=("content_items",),
        execution_enabled=True,
    ),
    MarketingSpecialistType.ANALYST: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.ANALYST,
        name="Analyst",
        description="Campaign performance and workflow analysis.",
        default_objective="Analyze campaign workflow and performance signals",
        default_expected_output="Fact-based recommendations for next steps",
        output_type="analysis",
        dependencies=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.CONTENT_PLANNER,
            MarketingSpecialistType.COPYWRITER,
            MarketingSpecialistType.CRITIC,
        ),
        structured_data_keys=(
            "risks",
            "resource_requirements",
            "channel_fit",
            "funnel_gaps",
            "execution_complexity",
            "kpi_recommendations",
        ),
        execution_enabled=True,
    ),
    MarketingSpecialistType.CRITIC: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.CRITIC,
        name="Critic",
        description="Quality review before publication.",
        default_objective="Review deliverables for clarity and brand fit",
        default_expected_output="Quality checklist and revision notes",
        output_type="critique",
        dependencies=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.CONTENT_PLANNER,
            MarketingSpecialistType.COPYWRITER,
        ),
        structured_data_keys=(
            "strengths",
            "weaknesses",
            "inconsistencies",
            "missing_information",
            "improvement_actions",
            "approval_recommendation",
        ),
        execution_enabled=True,
    ),
    MarketingSpecialistType.OFFER_STRATEGIST: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.OFFER_STRATEGIST,
        name="Offer Strategist",
        description="Offer design, USP, and value proposition framing.",
        default_objective="Define a compelling offer and unique value proposition",
        default_expected_output="Offer summary with USP and proof-backed value proposition",
        output_type="offer_strategy",
        dependencies=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
        ),
        structured_data_keys=(
            "core_offer",
            "value_proposition",
            "unique_mechanism",
            "offer_variants",
            "pricing_hypotheses",
            "risk_reversal",
            "positioning_statement",
        ),
        execution_enabled=True,
        out_of_scope=(
            "funnel architecture",
            "copy drafts",
            "ContentAsset creation",
        ),
    ),
    MarketingSpecialistType.FUNNEL_ARCHITECT: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.FUNNEL_ARCHITECT,
        name="Funnel Architect",
        description="Funnel mapping from awareness through retention.",
        default_objective="Design the marketing funnel stages and conversion path",
        default_expected_output="Stage map with entry points and retention loops",
        output_type="funnel_design",
        dependencies=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.OFFER_STRATEGIST,
        ),
        structured_data_keys=(
            "funnel_stages",
            "entry_points",
            "lead_capture",
            "nurture_sequence",
            "conversion_events",
            "retention_actions",
        ),
        execution_enabled=True,
        out_of_scope=(
            "lead magnet assets",
            "paid media buying",
            "auto-run pipeline tasks",
        ),
    ),
    MarketingSpecialistType.LEAD_MAGNET_SPECIALIST: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.LEAD_MAGNET_SPECIALIST,
        name="Lead Magnet Specialist",
        description="Lead magnets, quizzes, checklists, and entry offers.",
        default_objective="Propose lead capture assets aligned to the funnel",
        default_expected_output="Lead magnet concepts with formats and entry hooks",
        output_type="lead_magnet",
        dependencies=(
            MarketingSpecialistType.OFFER_STRATEGIST,
            MarketingSpecialistType.FUNNEL_ARCHITECT,
        ),
        structured_data_keys=(
            "lead_magnet_type",
            "title_variants",
            "promise",
            "delivery_format",
            "qualification_goal",
            "followup_recommendation",
        ),
        execution_enabled=True,
        out_of_scope=(
            "file generation",
            "landing page build",
            "CRM integration",
        ),
    ),
    MarketingSpecialistType.SALES_COPYWRITER: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.SALES_COPYWRITER,
        name="Sales Copywriter",
        description="Sales pages, landing pages, and direct-response offers.",
        default_objective="Draft conversion-focused sales page structure and copy blocks",
        default_expected_output="Landing sections with headlines, body, and CTAs",
        output_type="sales_copy",
        dependencies=(
            MarketingSpecialistType.OFFER_STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
        ),
        structured_data_keys=(
            "headline",
            "offer",
            "objections",
            "benefits",
            "cta",
            "sales_sections",
        ),
        execution_enabled=True,
        out_of_scope=(
            "replacing content_copywriter role",
            "ContentAsset rows",
            "publish or schedule",
        ),
    ),
    MarketingSpecialistType.EMAIL_DM_SPECIALIST: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.EMAIL_DM_SPECIALIST,
        name="Email/DM Specialist",
        description="Email sequences and Telegram/DM nurture flows.",
        default_objective="Design nurture sequences for email and messaging channels",
        default_expected_output="Multi-step sequence with subjects, hooks, and timing",
        output_type="email_sequence",
        dependencies=(
            MarketingSpecialistType.OFFER_STRATEGIST,
            MarketingSpecialistType.SALES_COPYWRITER,
        ),
        structured_data_keys=(
            "sequence_steps",
            "message_goals",
            "cta_map",
            "trigger_points",
            "followup_rules",
        ),
        execution_enabled=True,
        out_of_scope=(
            "ESP send",
            "Telegram bot dispatch",
            "automation triggers",
        ),
    ),
    MarketingSpecialistType.CRO_SPECIALIST: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.CRO_SPECIALIST,
        name="CRO Specialist",
        description="Conversion optimization for landing pages, CTAs, and trust elements.",
        default_objective="Recommend conversion improvements and test hypotheses",
        default_expected_output="CRO audit with prioritized actions and test hypotheses",
        output_type="cro_recommendations",
        dependencies=(
            MarketingSpecialistType.OFFER_STRATEGIST,
            MarketingSpecialistType.FUNNEL_ARCHITECT,
            MarketingSpecialistType.SALES_COPYWRITER,
        ),
        structured_data_keys=(
            "conversion_bottlenecks",
            "landing_page_recommendations",
            "cta_improvements",
            "trust_elements",
            "form_optimization",
            "test_hypotheses",
            "priority_actions",
        ),
        execution_enabled=True,
        out_of_scope=(
            "A/B test execution",
            "analytics ingestion",
            "ContentAsset creation",
        ),
    ),
    MarketingSpecialistType.SMM_STRATEGIST: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.SMM_STRATEGIST,
        name="SMM Strategist",
        description="Social media strategy aligned to offer and content plan.",
        default_objective="Design platform-focused social strategy and engagement plan",
        default_expected_output="SMM strategy with formats, cadence, and engagement hooks",
        output_type="smm_strategy",
        dependencies=(
            MarketingSpecialistType.STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.CONTENT_PLANNER,
            MarketingSpecialistType.OFFER_STRATEGIST,
        ),
        structured_data_keys=(
            "platform_focus",
            "content_formats",
            "posting_frequency",
            "engagement_hooks",
            "community_management_notes",
            "social_proof_ideas",
            "risks",
        ),
        execution_enabled=True,
        out_of_scope=(
            "post scheduling",
            "paid social buying",
            "ContentAsset rows",
        ),
    ),
    MarketingSpecialistType.AD_CREATIVE_STRATEGIST: MarketingSpecialistProfile(
        specialist_type=MarketingSpecialistType.AD_CREATIVE_STRATEGIST,
        name="Ad Creative Strategist",
        description="Paid creative angles, hooks, and variant matrices.",
        default_objective="Design ad creative strategy with hooks and testing matrix",
        default_expected_output="Creative angles, copy variants, and testing plan",
        output_type="ad_creative_strategy",
        dependencies=(
            MarketingSpecialistType.OFFER_STRATEGIST,
            MarketingSpecialistType.RESEARCHER,
            MarketingSpecialistType.SALES_COPYWRITER,
        ),
        structured_data_keys=(
            "creative_angles",
            "ad_hooks",
            "visual_concepts",
            "primary_text_variants",
            "headline_variants",
            "cta_variants",
            "testing_matrix",
        ),
        execution_enabled=True,
        out_of_scope=(
            "ad platform API",
            "media generation",
            "auto-publish",
        ),
    ),
}


def list_marketing_specialists() -> list[MarketingSpecialistProfile]:
    return [_REGISTRY[key] for key in MarketingSpecialistType]


def list_frozen_pipeline_specialists() -> list[MarketingSpecialistProfile]:
    return [_REGISTRY[key] for key in FROZEN_PIPELINE_ORDER]


def get_marketing_specialist(specialist_type: MarketingSpecialistType) -> MarketingSpecialistProfile:
    return _REGISTRY[specialist_type]
