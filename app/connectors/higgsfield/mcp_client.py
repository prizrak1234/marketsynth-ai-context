"""Minimal JSON-RPC MCP client for Higgsfield remote server (CONN-HF-01.1)."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import httpx

from app.connectors.higgsfield.constants import HIGGSFIELD_OFFICIAL_MCP_ENDPOINT
from app.core.config import Settings


class HiggsfieldMcpError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        self.message = message
        super().__init__(message or code)


class HiggsfieldMcpClient:
    """HTTP MCP client — initialize + tools/list + tools/call; no business logic."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._endpoint = settings.higgsfield_mcp_endpoint.rstrip("/")
        self._timeout = settings.higgsfield_mcp_timeout_seconds
        self._discovered_tools: list[str] | None = None
        self._discovered_tools_detailed: list[dict[str, Any]] | None = None
        self._last_auth_challenge: dict[str, Any] | None = None
        self._negotiated_protocol_version: str | None = None

    @property
    def configured(self) -> bool:
        return self._settings.higgsfield_mcp_configured

    @property
    def endpoint(self) -> str:
        return self._endpoint

    def endpoint_matches_official(self) -> bool:
        return self._endpoint == HIGGSFIELD_OFFICIAL_MCP_ENDPOINT.rstrip("/")

    def _auth_headers(self) -> dict[str, str]:
        token = self._settings.higgsfield_oauth_access_token
        if token is None:
            return {}
        raw = token.get_secret_value().strip()
        if not raw:
            return {}
        return {"Authorization": f"Bearer {raw}"}

    def authentication_findings(self) -> dict[str, Any]:
        has_token = bool(self._auth_headers())
        notes: list[str] = []
        mechanism = "unknown"
        if self._last_auth_challenge:
            mechanism = str(self._last_auth_challenge.get("mechanism") or "auth_challenge")
            notes.append("Authentication challenge observed during MCP handshake.")
        elif has_token:
            mechanism = "bearer_token_env"
            notes.append(
                "Bearer token supplied via environment — verified only if handshake succeeds."
            )
        else:
            mechanism = "unauthenticated_or_session"
            notes.append("No bearer token configured — server may require browser OAuth.")
        return {
            "mechanism": mechanism,
            "requires_bearer_token": has_token,
            "notes": notes,
            "auth_challenge": self._last_auth_challenge or {},
        }

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": method,
            "params": params or {},
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **self._auth_headers(),
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._endpoint, json=payload, headers=headers)
        if response.status_code in {401, 403}:
            self._last_auth_challenge = {
                "mechanism": "http_auth_required",
                "http_status": response.status_code,
            }
            raise HiggsfieldMcpError(
                "mcp_auth_required",
                f"HTTP {response.status_code}",
            )
        if response.status_code >= 400:
            raise HiggsfieldMcpError(
                "mcp_http_error",
                f"HTTP {response.status_code}",
            )
        body = response.json()
        if "error" in body:
            err = body["error"]
            code = str(err.get("code", "mcp_rpc_error"))
            if code in {"401", "403", "-32001"} or "auth" in str(err.get("message", "")).lower():
                self._last_auth_challenge = {
                    "mechanism": "mcp_auth_error",
                    "error_code": code,
                }
            raise HiggsfieldMcpError(code, str(err.get("message", "")))
        return body.get("result")

    async def initialize(self) -> dict[str, Any]:
        result = await self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "marketsynth", "version": "0.1.0"},
            },
        )
        parsed = result if isinstance(result, dict) else {}
        self._negotiated_protocol_version = str(parsed.get("protocolVersion") or "2024-11-05")
        return parsed

    async def list_tools(self, *, refresh: bool = False) -> list[str]:
        detailed = await self.list_tools_detailed(refresh=refresh)
        return [str(tool["name"]) for tool in detailed if tool.get("name")]

    async def list_tools_detailed(self, *, refresh: bool = False) -> list[dict[str, Any]]:
        if self._discovered_tools_detailed is not None and not refresh:
            return list(self._discovered_tools_detailed)
        result = await self._rpc("tools/list", {})
        tools: list[dict[str, Any]] = []
        if isinstance(result, dict):
            for item in result.get("tools") or []:
                if isinstance(item, dict) and item.get("name"):
                    tools.append(
                        {
                            "name": str(item["name"]),
                            "description": str(item.get("description") or ""),
                            "inputSchema": item.get("inputSchema") or {},
                        }
                    )
        self._discovered_tools_detailed = tools
        self._discovered_tools = [tool["name"] for tool in tools]
        return list(tools)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self._rpc(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )
        if not isinstance(result, dict):
            return {"raw": result}
        content = result.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text")
                    if isinstance(text, str):
                        try:
                            parsed = json.loads(text)
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            return {"text": text}
        return result

    def resolve_provider_tool_name(
        self,
        canonical_operation: str,
        *,
        mapping_store: Any | None = None,
    ) -> str | None:
        """Resolve canonical operation to verified provider tool name — no guessing."""
        from app.connectors.higgsfield.sandbox.operation_mapping import (
            OperationMappingStore,
            load_operation_mapping,
        )

        store = mapping_store or load_operation_mapping()
        if not isinstance(store, OperationMappingStore):
            store = OperationMappingStore()
        binding = store.get_binding(canonical_operation)
        if binding is None:
            return None
        discovered = set(store.discovered_tool_names())
        if discovered and binding.provider_tool_name not in discovered:
            return None
        return binding.provider_tool_name
