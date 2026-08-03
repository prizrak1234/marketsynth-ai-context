"""Allowlisted MCP servers and tools for CMVP.1."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.contracts import McpServerRole


@dataclass(frozen=True, slots=True)
class McpToolSpec:
    server_id: str
    server_role: McpServerRole
    tool_name: str
    schema_fingerprint: str
    read_only: bool = True


SEARCH_TOOL = McpToolSpec(
    server_id="xmlriver",
    server_role=McpServerRole.SEARCH_MCP,
    tool_name="search",
    schema_fingerprint="xmlriver_search_v1",
)

FETCH_TOOL = McpToolSpec(
    server_id="firecrawl",
    server_role=McpServerRole.WEB_FETCH_MCP,
    tool_name="fetch",
    schema_fingerprint="firecrawl_fetch_v1",
)

ALLOWED_TOOLS: dict[tuple[McpServerRole, str], McpToolSpec] = {
    (McpServerRole.SEARCH_MCP, "search"): SEARCH_TOOL,
    (McpServerRole.WEB_FETCH_MCP, "fetch"): FETCH_TOOL,
}


def get_tool_spec(server_role: McpServerRole, tool_name: str) -> McpToolSpec | None:
    return ALLOWED_TOOLS.get((server_role, tool_name))
