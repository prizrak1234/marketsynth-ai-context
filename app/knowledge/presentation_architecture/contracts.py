"""Shared contracts for Presentation Architecture."""

from __future__ import annotations

PRESENTATION_TYPES = frozenset(
    {
        "business_pitch",
        "sales_presentation",
        "investor_presentation",
        "market_research_report",
        "strategy_presentation",
        "project_status",
        "technical_architecture",
        "training",
        "internal_decision",
        "case_study",
        "product_demo_structure",
        "webinar",
        "conference_talk",
        "content_carousel_source",
        "custom",
    }
)

ARC_TYPES = frozenset(
    {
        "problem_solution",
        "situation_complication_resolution",
        "evidence_conclusion",
        "before_after_bridge",
        "opportunity_strategy_action",
        "educational_progression",
        "chronological",
        "comparison",
        "decision_memo",
        "technical_system_walkthrough",
        "custom",
    }
)

SLIDE_TYPES = frozenset(
    {
        "title",
        "agenda",
        "section_divider",
        "executive_summary",
        "problem",
        "market_context",
        "customer",
        "evidence",
        "comparison",
        "process",
        "architecture",
        "timeline",
        "metric",
        "chart",
        "case_study",
        "recommendation",
        "risk",
        "decision",
        "CTA",
        "appendix",
        "custom",
    }
)

CONTENT_BLOCK_TYPES = frozenset(
    {
        "headline",
        "short_text",
        "bullet_group",
        "quote",
        "metric",
        "comparison",
        "process_steps",
        "timeline",
        "table",
        "chart_placeholder",
        "image_placeholder",
        "diagram_placeholder",
        "callout",
        "warning",
        "source_note",
    }
)

VISUAL_TYPES = frozenset(
    {
        "photo",
        "illustration",
        "diagram",
        "process_diagram",
        "architecture_diagram",
        "comparison_visual",
        "timeline",
        "map",
        "icon_set",
        "abstract_background",
        "product_mockup",
        "screenshot_reference",
        "chart",
        "table",
        "other",
    }
)

CHART_TYPES = frozenset(
    {
        "bar",
        "line",
        "area",
        "scatter",
        "waterfall",
        "funnel",
        "pie",
        "donut",
        "table",
        "timeline",
        "heatmap",
        "matrix",
        "other",
    }
)

THEME_FAMILIES = frozenset(
    {
        "minimal",
        "business",
        "dark",
        "gradient",
        "technical",
        "colorful",
        "editorial",
        "custom_brand",
    }
)

PRESENTATION_READINESS = frozenset(
    {
        "ready_for_rendering_review",
        "partially_ready",
        "blocked_by_missing_content",
        "blocked_by_claim_risk",
        "insufficient_information",
        "conflicted",
        "out_of_scope",
    }
)

FORBIDDEN_OUTPUT_FIELDS = frozenset(
    {
        "rendered_file",
        "pptx_path",
        "pdf_path",
        "marp_output",
        "canva_design_id",
        "google_slides_id",
        "publication_result",
        "execution_status",
        "approval_granted",
    }
)

FORBIDDEN_INPUT_PATTERNS = frozenset(
    {
        "raw_css",
        "raw_html",
        "remote_font_url",
        "external_skill_package",
    }
)

MAX_SLIDE_DENSITY_POINTS = 12

SKILL_ID = "ms.skill.presentation_architecture"
SKILL_VERSION = "0.1.0"
