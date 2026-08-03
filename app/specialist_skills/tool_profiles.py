"""Per-specialist Tool Profiles (Phase H2.7).

Typed governance of which normalized BusinessTools a role may use. Hard denies
apply to ALL roles in this slice: no external execution (Make/n8n), no
advertising writes. Draft-only content path uses zero tools.
"""

from __future__ import annotations

from app.schemas.contracts import (
    BusinessToolCode,
    BusinessToolMode,
    ToolProfile,
)

# External execution and advertising writes are denied for every specialist
# in H2.7 slice 1 regardless of capability pack contents.
_GLOBAL_HARD_DENIES: tuple[BusinessToolCode, ...] = (
    BusinessToolCode.WORKFLOW_AUTOMATION,
    BusinessToolCode.ADVERTISING_PLATFORM,
)

_PROFILES: dict[str, ToolProfile] = {
    "content_specialist": ToolProfile(
        specialist_role="content_specialist",
        allowed_tools=[BusinessToolCode.KNOWLEDGE_RETRIEVAL],
        denied_tools=[
            BusinessToolCode.WEB_SEARCH,
            BusinessToolCode.SOURCE_FETCH,
            BusinessToolCode.WORKFLOW_AUTOMATION,
            BusinessToolCode.ADVERTISING_PLATFORM,
        ],
        mode=BusinessToolMode.READ,
        approval_required=False,
        max_calls=0,
        cost_ceiling_usd=0.0,
    ),
    "content_planner": ToolProfile(
        specialist_role="content_planner",
        allowed_tools=[BusinessToolCode.KNOWLEDGE_RETRIEVAL],
        denied_tools=list(_GLOBAL_HARD_DENIES),
        mode=BusinessToolMode.READ,
        approval_required=False,
    ),
    "visual_specialist": ToolProfile(
        specialist_role="visual_specialist",
        allowed_tools=[
            BusinessToolCode.KNOWLEDGE_RETRIEVAL,
            BusinessToolCode.IMAGE_GENERATION,
        ],
        denied_tools=list(_GLOBAL_HARD_DENIES),
        mode=BusinessToolMode.READ,
        approval_required=False,
        max_calls=1,
    ),
    "researcher": ToolProfile(
        specialist_role="researcher",
        # Declared for later slices; research execution is NOT enabled in slice 1.
        allowed_tools=[
            BusinessToolCode.KNOWLEDGE_RETRIEVAL,
            BusinessToolCode.WEB_SEARCH,
            BusinessToolCode.SOURCE_FETCH,
            BusinessToolCode.STRUCTURED_EXTRACTION,
        ],
        denied_tools=list(_GLOBAL_HARD_DENIES) + [BusinessToolCode.IMAGE_GENERATION],
        mode=BusinessToolMode.READ,
        approval_required=True,
    ),
    "strategist": ToolProfile(
        specialist_role="strategist",
        allowed_tools=[BusinessToolCode.KNOWLEDGE_RETRIEVAL],
        denied_tools=list(_GLOBAL_HARD_DENIES),
        mode=BusinessToolMode.READ,
        approval_required=True,
    ),
    "programmer": ToolProfile(
        specialist_role="programmer",
        allowed_tools=[BusinessToolCode.KNOWLEDGE_RETRIEVAL],
        denied_tools=list(_GLOBAL_HARD_DENIES)
        + [
            BusinessToolCode.WEB_SEARCH,
            BusinessToolCode.SOURCE_FETCH,
            BusinessToolCode.IMAGE_GENERATION,
        ],
        mode=BusinessToolMode.READ,
        approval_required=False,
    ),
}


def get_tool_profile(specialist_role: str) -> ToolProfile | None:
    profile = _PROFILES.get(specialist_role)
    if profile is None:
        return None
    # Enforce global hard denies defensively even if a profile omitted them.
    denied = set(profile.denied_tools) | set(_GLOBAL_HARD_DENIES)
    allowed = [t for t in profile.allowed_tools if t not in _GLOBAL_HARD_DENIES]
    return profile.model_copy(
        update={"allowed_tools": allowed, "denied_tools": sorted(denied, key=lambda t: t.value)}
    )


def list_tool_profiles() -> list[ToolProfile]:
    return [get_tool_profile(role) for role in _PROFILES]  # type: ignore[misc]


def tool_allowed(specialist_role: str, tool: BusinessToolCode) -> bool:
    profile = get_tool_profile(specialist_role)
    if profile is None:
        return False
    if tool in profile.denied_tools:
        return False
    return tool in profile.allowed_tools


def assert_tool_allowed(specialist_role: str, tool: BusinessToolCode) -> None:
    """Raise PermissionError when a specialist may not use a tool."""
    if not tool_allowed(specialist_role, tool):
        raise PermissionError(
            f"tool_denied: role={specialist_role} tool={tool.value}"
        )
