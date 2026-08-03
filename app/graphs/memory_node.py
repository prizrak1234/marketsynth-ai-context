"""Graph memory-load layer — project-scoped context before prompt build."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.memory_service import MemoryService
from app.tools.executors.memory_search import _format_memory_item
from app.tools.security import sanitize_tool_payload


@dataclass(frozen=True)
class GraphMemoryLoadResult:
    status: str
    memory_context: dict[str, Any] | list[Any] | None
    item_count: int
    memory_query: str | None


def resolve_memory_search_query(input_payload: dict[str, Any]) -> str | None:
    """Derive a search query from explicit memory_query or prompt text."""
    explicit = input_payload.get("memory_query")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    prompt = input_payload.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip()

    return None


def _safe_query_for_state(query: str) -> str:
    sanitized = sanitize_tool_payload({"query": query})
    value = sanitized.get("query", "")
    if not isinstance(value, str):
        value = str(value)
    return value[:240]


def build_memory_context_from_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "source": "graph_memory_load",
        "count": len(items),
        "items": items,
    }


async def load_graph_memory_context(
    session: AsyncSession,
    *,
    owner_id: UUID,
    project_id: UUID,
    agent_id: UUID,
    input_payload: dict[str, Any],
    provided_memory_context: Any | None,
    skip_graph_memory_load: bool,
) -> GraphMemoryLoadResult:
    """Load memory for the graph path unless caller supplied context or opted out."""
    if provided_memory_context is not None:
        sanitized = sanitize_tool_payload(provided_memory_context)
        count = len(sanitized) if isinstance(sanitized, list) else 1
        return GraphMemoryLoadResult(
            status="input_provided",
            memory_context=sanitized,
            item_count=count,
            memory_query=None,
        )

    settings = get_settings()
    if skip_graph_memory_load or not settings.graph_memory_enabled:
        return GraphMemoryLoadResult(
            status="skipped",
            memory_context=None,
            item_count=0,
            memory_query=None,
        )

    query = resolve_memory_search_query(input_payload)
    if query is None:
        return GraphMemoryLoadResult(
            status="empty",
            memory_context=None,
            item_count=0,
            memory_query=None,
        )

    memory = MemoryService(session)
    rows = await memory.search(
        user_id=owner_id,
        project_id=project_id,
        query=query,
        agent_id=agent_id,
        limit=settings.graph_memory_limit,
    )
    items = [_format_memory_item(row) for row in rows]
    if not items:
        return GraphMemoryLoadResult(
            status="empty",
            memory_context=None,
            item_count=0,
            memory_query=_safe_query_for_state(query),
        )

    return GraphMemoryLoadResult(
        status="loaded",
        memory_context=build_memory_context_from_items(items),
        item_count=len(items),
        memory_query=_safe_query_for_state(query),
    )
