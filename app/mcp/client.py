"""Minimal MCP client — allowlist, audit, timeout, retry."""

from __future__ import annotations

import asyncio
import time
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.business_tools.contracts import BusinessToolError, SourceFetchResult, WebSearchResult
from app.core.config import Settings
from app.core.exceptions import InvalidStateError
from app.db.base import utc_now
from app.db.models.mcp_tool_call_audit import McpToolCallAuditTable
from app.db.repositories.mcp_tool_call_audits import McpToolCallAuditRepository
from app.mcp.adapters.firecrawl_fetch import FirecrawlFetchMcpAdapter
from app.mcp.adapters.xmlriver_search import XmlRiverSearchMcpAdapter
from app.mcp.registry import FETCH_TOOL, SEARCH_TOOL, get_tool_spec
from app.mcp.security import sanitize_tool_output, summarize_request
from app.schemas.contracts import McpServerRole, McpToolCallStatus
from app.services.transaction import transactional


class McpClient:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._audits = McpToolCallAuditRepository(session)
        self._search = XmlRiverSearchMcpAdapter(settings)
        self._fetch = FirecrawlFetchMcpAdapter(settings)

    async def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "server_role": SEARCH_TOOL.server_role.value,
                "server_id": SEARCH_TOOL.server_id,
                "tool_name": SEARCH_TOOL.tool_name,
                "schema_fingerprint": SEARCH_TOOL.schema_fingerprint,
                "read_only": SEARCH_TOOL.read_only,
            },
            {
                "server_role": FETCH_TOOL.server_role.value,
                "server_id": FETCH_TOOL.server_id,
                "tool_name": FETCH_TOOL.tool_name,
                "schema_fingerprint": FETCH_TOOL.schema_fingerprint,
                "read_only": FETCH_TOOL.read_only,
            },
        ]

    async def invoke_search(
        self,
        *,
        owner_id: UUID,
        user_request_id: UUID,
        investigation_id: UUID | None,
        query: str,
        limit: int = 5,
    ) -> tuple[WebSearchResult, UUID]:
        return await self._invoke(
            owner_id=owner_id,
            user_request_id=user_request_id,
            investigation_id=investigation_id,
            server_role=McpServerRole.SEARCH_MCP,
            tool_name="search",
            payload={"query": query, "limit": limit},
            runner=lambda: self._search.search(query, limit=limit),
        )

    async def invoke_fetch(
        self,
        *,
        owner_id: UUID,
        user_request_id: UUID,
        investigation_id: UUID | None,
        url: str,
    ) -> tuple[SourceFetchResult, UUID]:
        return await self._invoke(
            owner_id=owner_id,
            user_request_id=user_request_id,
            investigation_id=investigation_id,
            server_role=McpServerRole.WEB_FETCH_MCP,
            tool_name="fetch",
            payload={"url": url},
            runner=lambda: self._fetch.fetch(url),
        )

    async def _invoke(
        self,
        *,
        owner_id: UUID,
        user_request_id: UUID,
        investigation_id: UUID | None,
        server_role: McpServerRole,
        tool_name: str,
        payload: dict[str, Any],
        runner,
    ):
        if not self._settings.mcp_read_only_enabled:
            raise InvalidStateError("mcp_disabled")

        spec = get_tool_spec(server_role, tool_name)
        if spec is None:
            raise InvalidStateError("mcp_tool_not_allowed")

        timeout = self._settings.mcp_tool_call_timeout_seconds
        max_retries = self._settings.mcp_max_retries
        max_bytes = self._settings.mcp_max_response_bytes

        last_error: str | None = None
        for attempt in range(max_retries + 1):
            started = time.perf_counter()
            status = McpToolCallStatus.SUCCESS
            error_code: str | None = None
            response_summary: dict[str, Any] = {}
            result = None
            try:
                result = await asyncio.wait_for(runner(), timeout=timeout)
                if isinstance(result, WebSearchResult):
                    size = sum(len(c.url) + len(c.title) + len(c.snippet) for c in result.candidates)
                else:
                    size = len(result.normalized_text_excerpt or "")
                if size > max_bytes:
                    raise InvalidStateError("mcp_response_too_large")
                if isinstance(result, SourceFetchResult):
                    result.normalized_text_excerpt = sanitize_tool_output(
                        result.normalized_text_excerpt,
                        max_len=max_bytes,
                    )
                response_summary = {"size_bytes": size, "attempt": attempt + 1}
            except TimeoutError:
                status = McpToolCallStatus.TIMEOUT
                error_code = "timeout"
                last_error = "timeout"
            except InvalidStateError as exc:
                status = McpToolCallStatus.BLOCKED if str(exc) == "mcp_response_too_large" else McpToolCallStatus.ERROR
                error_code = str(exc)
                last_error = error_code
                if status == McpToolCallStatus.BLOCKED:
                    break
            except BusinessToolError as exc:
                status = McpToolCallStatus.ERROR
                error_code = exc.category
                last_error = exc.category
            except Exception:  # noqa: BLE001
                status = McpToolCallStatus.ERROR
                error_code = "provider_error"
                last_error = "provider_error"

            duration_ms = int((time.perf_counter() - started) * 1000)
            audit_row = McpToolCallAuditTable(
                owner_id=owner_id,
                tenant_id=owner_id,
                user_request_id=user_request_id,
                investigation_id=investigation_id,
                server_role=server_role,
                server_id=spec.server_id,
                tool_name=tool_name,
                tool_schema_fingerprint=spec.schema_fingerprint,
                status=status,
                duration_ms=duration_ms,
                response_size_bytes=int(response_summary.get("size_bytes") or 0),
                error_code=error_code,
                request_summary=summarize_request(payload),
                response_summary=response_summary,
                created_at=utc_now(),
            )
            async with transactional(self._session):
                saved = await self._audits.create(audit_row)

            if status == McpToolCallStatus.SUCCESS and result is not None:
                return result, saved.id

            if attempt >= max_retries:
                raise InvalidStateError(last_error or "mcp_invoke_failed")

        raise InvalidStateError(last_error or "mcp_invoke_failed")
