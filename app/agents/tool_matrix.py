"""Marketing agent tool access matrix (Phase 5.8 — docs/tests, not runtime enforcement)."""

from __future__ import annotations

from typing import Any, TypedDict

from app.core.config import Settings, get_settings
from app.schemas.contracts import AgentType
from app.tools.agent_tool_profiles import get_agent_tool_allowlist
from app.tools.marketing_tools import (
    CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME,
    CONTENT_ASSET_CREATE_REVISION_TOOL_NAME,
)
from app.tools.write_tool_settings import (
    CREATE_DRAFT_ALLOWED_AGENT_TYPES,
    CREATE_REVISION_ALLOWED_AGENT_TYPES,
)

MARKETING_AGENT_TYPES: frozenset[AgentType] = frozenset(
    {
        AgentType.ORCHESTRATOR,
        AgentType.STRATEGIST,
        AgentType.RESEARCHER,
        AgentType.CONTENT_PLANNER,
        AgentType.COPYWRITER,
        AgentType.CRITIC,
    },
)

SPECIALIST_AGENT_TYPES: frozenset[AgentType] = frozenset(
    MARKETING_AGENT_TYPES - {AgentType.ORCHESTRATOR},
)

AGENT_MATRIX_NOTES: dict[AgentType, str] = {
    AgentType.GENERAL: "Top-level router only — no tools.",
    AgentType.PROGRAMMER: "Consultation-only skeleton (AI.16). No shell, repo, or deploy tools.",
    AgentType.MEDIA: "Visual brief skeleton (AI.17). No image/video generation or design-tool APIs.",
    AgentType.ORCHESTRATOR: (
        "Supervisor — read-only context + optional create_draft; delegates specialist work "
        "via LangGraph handoff. No approve/publish."
    ),
    AgentType.STRATEGIST: "Strategy drafts only (article). No funnel link mutations.",
    AgentType.RESEARCHER: "Internal research memo (article). No web search in Phase 5.",
    AgentType.CONTENT_PLANNER: "Content plan drafts. Proposes step assets; humans link in UI.",
    AgentType.COPYWRITER: "Channel copy drafts (email, ads, posts, landing).",
    AgentType.CRITIC: "Review drafts; never edits source asset.",
    AgentType.ANALYST: "Read-only metrics context. No marketing drafts.",
}

FORBIDDEN_AGENT_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "content_asset.approve",
        "content_asset.publish",
        "content_asset.update",
        "content_asset.archive",
        "memory.write",
        "task.create",
        "agent.update",
    },
)


class AgentWriteCapabilities(TypedDict):
    create_draft_allowed: bool
    create_draft_visible: bool
    write_globally_enabled: bool
    create_draft_globally_enabled: bool


class AgentToolMatrixEntry(TypedDict):
    read: list[str]
    write: list[str]


def _write_flags(settings: Settings) -> tuple[bool, bool, bool]:
    write_global = bool(settings.agent_write_tools_enabled)
    create_draft_global = bool(
        settings.agent_write_tools_enabled
        and settings.agent_write_tool_content_asset_create_draft_enabled,
    )
    create_revision_global = bool(
        settings.agent_write_tools_enabled
        and settings.agent_write_tool_content_asset_revision_enabled,
    )
    return write_global, create_draft_global, create_revision_global


def get_agent_write_capabilities(
    settings: Settings | None = None,
) -> dict[str, AgentWriteCapabilities]:
    """Per-agent-type write capability flags derived from settings (not LLM exposure)."""
    active = settings or get_settings()
    write_global, create_draft_global, _create_revision_global = _write_flags(active)
    result: dict[str, AgentWriteCapabilities] = {}
    for agent_type in AgentType:
        allowed_type = agent_type in CREATE_DRAFT_ALLOWED_AGENT_TYPES
        result[agent_type.value] = AgentWriteCapabilities(
            create_draft_allowed=allowed_type,
            create_draft_visible=allowed_type and create_draft_global,
            write_globally_enabled=write_global,
            create_draft_globally_enabled=create_draft_global,
        )
    return result


def get_agent_tool_matrix(
    settings: Settings | None = None,
) -> dict[str, AgentToolMatrixEntry]:
    """
    Effective tool matrix: read tools from static allowlist; write = create_draft when enabled.

    Keys are agent type strings (e.g. ``strategist``).
    """
    active = settings or get_settings()
    _write_global, create_draft_global, create_revision_global = _write_flags(active)
    matrix: dict[str, AgentToolMatrixEntry] = {}
    for agent_type in AgentType:
        read_tools = sorted(get_agent_tool_allowlist(agent_type))
        write_tools: list[str] = []
        if create_draft_global and agent_type in CREATE_DRAFT_ALLOWED_AGENT_TYPES:
            write_tools.append(CONTENT_ASSET_CREATE_DRAFT_TOOL_NAME)
        if create_revision_global and agent_type in CREATE_REVISION_ALLOWED_AGENT_TYPES:
            write_tools.append(CONTENT_ASSET_CREATE_REVISION_TOOL_NAME)
        matrix[agent_type.value] = AgentToolMatrixEntry(
            read=read_tools,
            write=write_tools,
        )
    return matrix


def build_tool_matrix_api_payload(
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Response shape for GET /agents/tool-matrix (no secrets)."""
    active = settings or get_settings()
    write_global, create_draft_global, _create_revision_global = _write_flags(active)
    matrix = get_agent_tool_matrix(active)
    agents = []
    for agent_type in AgentType:
        entry = matrix[agent_type.value]
        agents.append(
            {
                "agent_type": agent_type.value,
                "read_tools": entry["read"],
                "write_tools": entry["write"],
                "write_enabled": bool(entry["write"]),
                "notes": AGENT_MATRIX_NOTES.get(agent_type, ""),
            },
        )
    return {
        "write_globally_enabled": write_global,
        "create_draft_globally_enabled": create_draft_global,
        "agents": agents,
    }
