"""Default agent registry templates — technical metadata only, no LLM prompts."""

from __future__ import annotations

from typing import Any, TypedDict

from app.schemas.contracts import AgentCapability, AgentType


class AgentTemplate(TypedDict):
    name: str
    description: str
    default_config: dict[str, Any]
    capabilities: list[AgentCapability]


def _cap(
    name: str,
    description: str,
    *,
    input_schema: dict[str, Any] | None = None,
    output_schema: dict[str, Any] | None = None,
) -> AgentCapability:
    return AgentCapability(
        name=name,
        description=description,
        input_schema=input_schema or {"type": "object", "properties": {}},
        output_schema=output_schema or {"type": "object", "properties": {}},
    )


DEFAULT_AGENT_TEMPLATES: dict[AgentType, AgentTemplate] = {
    AgentType.GENERAL: {
        "name": "General Agent",
        "description": (
            "Top-level router — detects domain and delegates to specialists "
            "(marketing, programmer, media)."
        ),
        "default_config": {
            "routing": {
                "domains": ["marketing", "programmer", "media"],
            },
        },
        "capabilities": [
            _cap("route_to_domain", "Detect request domain and delegate to specialist agents"),
        ],
    },
    AgentType.PROGRAMMER: {
        "name": "Programmer",
        "description": (
            "Technical consultant — explains architecture, drafts specs and pseudocode. "
            "No repository, shell, deploy, or live integrations (AI.16 skeleton)."
        ),
        "default_config": {
            "llm": {
                "provider": "mock",
                "model": "mock-model",
                "temperature": 0.2,
                "max_tokens": 2000,
            },
            "tools": {
                "profile": "programmer",
            },
            "safety": {
                "shell": False,
                "filesystem": False,
                "github": False,
                "deploy": False,
                "live_telegram_bot": False,
            },
        },
        "capabilities": [
            _cap(
                "technical_consultation",
                "Explain approaches and trade-offs without executing code",
            ),
            _cap(
                "draft_technical_task",
                "Produce an in-memory technical task draft for human review",
            ),
        ],
    },
    AgentType.MEDIA: {
        "name": "Media",
        "description": (
            "Visual consultant — creative concepts, banner structure, designer briefs, "
            "and shot lists. No image/video generation or design-tool integrations (AI.17)."
        ),
        "default_config": {
            "llm": {
                "provider": "mock",
                "model": "mock-model",
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            "tools": {
                "profile": "media",
            },
            "safety": {
                "image_generation": False,
                "video_generation": False,
                "canva": False,
                "figma": False,
                "heygen": False,
                "file_write": False,
            },
        },
        "capabilities": [
            _cap(
                "visual_consultation",
                "Advise on layout, format, and creative direction without generating assets",
            ),
            _cap(
                "draft_visual_brief",
                "Produce an in-memory visual brief for human designers",
            ),
        ],
    },
    AgentType.STRATEGIST: {
        "name": "Strategist",
        "description": (
            "Marketing strategist — reads briefs, funnels, and assets; "
            "runs gap analysis and drafts strategy recommendations."
        ),
        "default_config": {
            "llm": {
                "provider": "mock",
                "model": "mock-model",
                "temperature": 0.3,
                "max_tokens": 1800,
            },
            "tools": {
                "profile": "strategist",
            },
            "output": {
                "default_asset_type": "article",
                "default_asset_title": "Marketing Strategy Draft",
            },
        },
        "capabilities": [
            _cap("read_project_context", "Read compact project context via tools"),
            _cap("read_marketing_briefs", "Read marketing briefs in the current project"),
            _cap("read_content_assets", "Read content assets linked to the campaign"),
            _cap("read_marketing_funnels", "Read funnel structure and step assets"),
            _cap("analyze_funnel_gaps", "Run heuristic funnel gap analysis"),
            _cap(
                "create_strategy_draft",
                "Create a draft strategy content asset when write tools are enabled",
            ),
        ],
    },
    AgentType.RESEARCHER: {
        "name": "Researcher",
        "description": (
            "Internal researcher — synthesizes briefs, assets, funnels, and memory "
            "into a structured research memo (no external web search)."
        ),
        "default_config": {
            "llm": {
                "provider": "mock",
                "model": "mock-model",
                "temperature": 0.25,
                "max_tokens": 1800,
            },
            "tools": {
                "profile": "researcher",
            },
            "output": {
                "default_asset_type": "article",
                "default_asset_title": "Research Draft",
            },
        },
        "capabilities": [
            _cap("read_project_context", "Read compact project context via tools"),
            _cap("read_memory", "Search project memory for prior research notes"),
            _cap("read_marketing_briefs", "Read marketing briefs in the current project"),
            _cap("read_content_assets", "Read existing content assets for context"),
            _cap("read_marketing_funnels", "Read funnel structure and run gap analysis"),
            _cap(
                "create_research_draft",
                "Create a draft research asset when write tools are enabled",
            ),
        ],
    },
    AgentType.COPYWRITER: {
        "name": "Copywriter",
        "description": (
            "Production copywriter — reads briefs, assets, and funnel context; "
            "creates draft content assets (email, ads, posts, landing blocks)."
        ),
        "default_config": {
            "llm": {
                "provider": "mock",
                "model": "mock-model",
                "temperature": 0.5,
                "max_tokens": 1600,
            },
            "tools": {
                "profile": "copywriter",
            },
            "output": {
                "default_asset_type": "email",
                "default_asset_title": "Copy Draft",
            },
        },
        "capabilities": [
            _cap("read_marketing_briefs", "Read marketing briefs in the current project"),
            _cap("read_content_assets", "Read content assets for source and reference copy"),
            _cap("read_funnel_context", "Read funnel steps and linked assets for context"),
            _cap(
                "create_copy_draft",
                "Create a draft content asset when write tools are enabled",
            ),
        ],
    },
    AgentType.CONTENT_PLANNER: {
        "name": "Content Planner",
        "description": (
            "Content planner — reads briefs, funnels, assets, and gap analysis; "
            "drafts a structured content plan asset (assets per step, priority order)."
        ),
        "default_config": {
            "llm": {
                "provider": "mock",
                "model": "mock-model",
                "temperature": 0.4,
                "max_tokens": 1800,
            },
            "tools": {
                "profile": "content_planner",
            },
            "output": {
                "default_asset_type": "article",
                "default_asset_title": "Content Plan Draft",
            },
        },
        "capabilities": [
            _cap("read_marketing_briefs", "Read marketing briefs in the current project"),
            _cap("read_content_assets", "Read existing content assets for context"),
            _cap("read_marketing_funnels", "Read funnel structure and step-linked assets"),
            _cap("analyze_funnel_gaps", "Run heuristic funnel gap analysis"),
            _cap(
                "create_content_plan_draft",
                "Create a draft content plan asset when write tools are enabled",
            ),
        ],
    },
    AgentType.CRITIC: {
        "name": "Critic",
        "description": (
            "Quality critic — reads briefs, funnels, and source assets; "
            "produces a structured review draft without editing the source."
        ),
        "default_config": {
            "llm": {
                "provider": "mock",
                "model": "mock-model",
                "temperature": 0.2,
                "max_tokens": 1600,
            },
            "tools": {
                "profile": "critic",
            },
            "output": {
                "default_asset_type": "article",
                "default_asset_title": "Content Review Draft",
            },
        },
        "capabilities": [
            _cap("read_marketing_briefs", "Read marketing briefs in the current project"),
            _cap("read_content_assets", "Read content assets under review and references"),
            _cap("read_marketing_funnels", "Read funnel structure and step-linked assets"),
            _cap(
                "review_content_quality",
                "Assess copy structure, CTA, and alignment with brief context",
            ),
            _cap(
                "create_review_draft",
                "Create a draft review asset when write tools are enabled",
            ),
        ],
    },
    AgentType.ANALYST: {
        "name": "Analyst",
        "description": "Tracks KPIs and produces performance summaries.",
        "default_config": {"report_window_days": 7},
        "capabilities": [
            _cap("analyze_metrics", "Analyze metrics for a project window"),
            _cap("report_insights", "Produce structured insight report"),
        ],
    },
    AgentType.ORCHESTRATOR: {
        "name": "Orchestrator",
        "description": (
            "Marketing orchestrator — reads project, brief, funnel, and asset context; "
            "delegates work to specialist agents via LangGraph handoff."
        ),
        "default_config": {
            "llm": {
                "provider": "mock",
                "model": "mock-model",
                "temperature": 0.2,
                "max_tokens": 1800,
            },
            "tools": {"profile": "orchestrator"},
            "orchestration": {
                "handoff_enabled": True,
                "max_child_runs": 3,
                "default_inline_child_execution": False,
            },
        },
        "capabilities": [
            _cap("read_project_context", "Read compact project context via tools"),
            _cap("read_marketing_briefs", "Read marketing briefs in the current project"),
            _cap("read_content_assets", "Read content assets linked to the campaign"),
            _cap("read_marketing_funnels", "Read funnel structure and step assets"),
            _cap("analyze_funnel_gaps", "Run heuristic funnel gap analysis"),
            _cap(
                "delegate_to_specialists",
                "Delegate work to specialist agents via graph handoff controls",
            ),
            _cap(
                "coordinate_marketing_workflow",
                "Coordinate multi-step marketing work across specialists",
            ),
        ],
    },
}
