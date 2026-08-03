"""Owner-only Higgsfield MCP sandbox handshake (CONN-HF-01.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.connectors.evidence import hash_payload
from app.connectors.higgsfield.constants import HIGGSFIELD_OFFICIAL_MCP_ENDPOINT
from app.connectors.higgsfield.mcp_client import HiggsfieldMcpClient, HiggsfieldMcpError
from app.connectors.higgsfield.sandbox.snapshot import (
    sanitize_snapshot_payload,
    write_sandbox_artifacts,
)
from app.core.config import Settings


class HiggsfieldSandboxHandshake:
    """Performs initialize + tools/list and writes sanitized sandbox artifacts."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = HiggsfieldMcpClient(settings)

    @property
    def endpoint(self) -> str:
        return self._settings.higgsfield_mcp_endpoint.rstrip("/")

    def endpoint_matches_official(self) -> bool:
        return self.endpoint == HIGGSFIELD_OFFICIAL_MCP_ENDPOINT.rstrip("/")

    async def run(self) -> dict[str, Any]:
        if not self.endpoint_matches_official():
            raise HiggsfieldMcpError(
                "endpoint_mismatch",
                "Endpoint must match official Higgsfield MCP URL.",
            )

        init_result = await self._client.initialize()
        tools = await self._client.list_tools_detailed(refresh=True)
        auth_findings = self._client.authentication_findings()

        tool_schema_hashes = {
            tool["name"]: hash_payload(tool.get("inputSchema") or {})
            for tool in tools
            if tool.get("name")
        }

        now = datetime.now(UTC).isoformat()
        server_capabilities = sanitize_snapshot_payload(
            {
                "negotiated_protocol_version": init_result.get("protocolVersion"),
                "server_info": init_result.get("serverInfo"),
                "capabilities": init_result.get("capabilities"),
                "endpoint": self.endpoint,
                "captured_at": now,
            }
        )
        tools_snapshot = sanitize_snapshot_payload(
            {
                "status": "captured",
                "captured_at": now,
                "tool_count": len(tools),
                "tools": tools,
            }
        )
        authentication_payload = sanitize_snapshot_payload(
            {
                "mechanism": auth_findings.get("mechanism", "unknown"),
                "requires_bearer_token": auth_findings.get("requires_bearer_token", False),
                "notes": auth_findings.get("notes", []),
                "captured_at": now,
            }
        )
        operation_mapping = {
            "status": "tools_discovered_pending_mapping",
            "verified_at": None,
            "mappings": {},
            "note": "Provider tool names must be mapped manually after tools/list review.",
        }
        freeze_manifest = {
            "status": "tools_discovered_pending_mapping",
            "phase": "CONN-HF-01.1L",
            "captured_at": now,
            "protocol_version": init_result.get("protocolVersion"),
            "tool_count": len(tools),
            "production_eligible": False,
            "customer_live_generation": False,
            "tenant_enabled": False,
            "video_enabled": False,
        }

        write_sandbox_artifacts(
            server_capabilities=server_capabilities,
            tools_snapshot=tools_snapshot,
            tool_schema_hashes=tool_schema_hashes,
            operation_mapping=operation_mapping,
            authentication_findings=authentication_payload,
            freeze_manifest=freeze_manifest,
        )

        return {
            "protocol_version": init_result.get("protocolVersion"),
            "tool_names": [tool["name"] for tool in tools if tool.get("name")],
            "tool_count": len(tools),
            "authentication": authentication_payload,
            "status": "tools_discovered_pending_mapping",
        }
