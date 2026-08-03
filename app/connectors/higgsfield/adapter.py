"""Higgsfield connector adapter — live execution only after sandbox verification."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.connectors.contracts import (
    ConnectorDescriptor,
    ConnectorExecutionRequest,
    ConnectorExecutionResult,
    ConnectorExecutionResultStatus,
    ConnectorHealthState,
    ConnectorToolDefinition,
)
from app.connectors.evidence import attach_evidence_to_result, redact_provider_metadata
from app.connectors.higgsfield.constants import MEDIA_OP_VIDEO_GENERATE
from app.connectors.higgsfield.descriptor import all_higgsfield_tools, higgsfield_descriptor
from app.connectors.higgsfield.mcp_client import HiggsfieldMcpClient, HiggsfieldMcpError
from app.connectors.higgsfield.sandbox.operation_mapping import load_operation_mapping
from app.core.config import Settings


class HiggsfieldConnectorAdapter:
    """MCP-derived renderer adapter — maps canonical operations to verified MCP tools."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = HiggsfieldMcpClient(settings)
        self._descriptor = higgsfield_descriptor(settings)
        self._tools = all_higgsfield_tools()
        self._mapping = load_operation_mapping()

    def describe_connector(self) -> ConnectorDescriptor:
        return self._descriptor

    def list_tools(self) -> tuple[ConnectorToolDefinition, ...]:
        return tuple(self._tools.values())

    def validate_configuration(self) -> tuple[str, ...]:
        issues: list[str] = []
        if not self._settings.higgsfield_mcp_enabled:
            issues.append("higgsfield_mcp_disabled")
        if not self._settings.higgsfield_sandbox_verified:
            issues.append("higgsfield_sandbox_not_verified")
        if not self._settings.higgsfield_mcp_configured:
            issues.append("higgsfield_oauth_token_missing")
        return tuple(issues)

    def health_check(self) -> ConnectorHealthState:
        issues = self.validate_configuration()
        if issues:
            return ConnectorHealthState.UNAVAILABLE
        return ConnectorHealthState.HEALTHY

    def execute_tool(self, request: ConnectorExecutionRequest) -> ConnectorExecutionResult:
        """Sync path rejected — live calls must use execute_tool_async."""
        started = datetime.now(UTC)
        if request.dry_run:
            return self._failed(request, started, "dry_run_not_supported_by_adapter")
        return self._failed(request, started, "use_async_execution_path")

    async def execute_tool_async(
        self, request: ConnectorExecutionRequest
    ) -> ConnectorExecutionResult:
        """Async execution path used by MediaRendererService for verified live calls only."""
        started = datetime.now(UTC)
        tool = self._tools.get(request.tool_id)
        if tool is None:
            return self._failed(request, started, "tool_not_found")

        if request.dry_run:
            return self._failed(request, started, "dry_run_not_supported_by_adapter")

        if not self._settings.higgsfield_mcp_live_calls_allowed:
            return self._blocked(request, tool, started, "connector_not_production_ready")

        if (
            request.tool_id == MEDIA_OP_VIDEO_GENERATE
            and not self._settings.higgsfield_video_render_enabled
        ):
            return self._blocked(request, tool, started, "higgsfield_video_render_disabled")

        provider_tool = self._client.resolve_provider_tool_name(
            request.tool_id,
            mapping_store=self._mapping,
        )
        if provider_tool is None:
            return self._failed(request, started, "provider_tool_not_mapped")

        tools_detailed = await self._client.list_tools_detailed()
        schema = next(
            (
                item.get("inputSchema") or {}
                for item in tools_detailed
                if item.get("name") == provider_tool
            ),
            {},
        )
        if not self._mapping.verify_schema_hash(provider_tool, schema):
            return self._failed(request, started, "provider_tool_schema_drift")

        try:
            payload = self._build_mcp_arguments(request)
            raw = await self._client.call_tool(provider_tool, payload)
        except HiggsfieldMcpError as exc:
            return self._failed(request, started, exc.code, safe_details={"message": exc.message})
        except Exception as exc:  # noqa: BLE001
            return self._failed(
                request,
                started,
                "provider_error",
                safe_details={"type": type(exc).__name__},
            )

        finished = datetime.now(UTC)
        job_id = str(raw.get("job_id") or raw.get("id") or uuid4())
        safe_output = {
            "job_id": job_id,
            "status": raw.get("status") or "submitted",
            "result_url": _redact_url(str(raw.get("url") or raw.get("result_url") or "") or None),
            "mime_type": raw.get("mime_type"),
            "provider_status": raw.get("status"),
        }
        result = ConnectorExecutionResult(
            request_id=request.request_id,
            connector_id=request.connector_id,
            connector_version=request.connector_version,
            tool_id=request.tool_id,
            status=ConnectorExecutionResultStatus.SUCCEEDED,
            output_payload=safe_output,
            safe_provider_metadata=redact_provider_metadata(
                {
                    "provider": "higgsfield_mcp",
                    "canonical_operation": request.tool_id,
                    "provider_tool": provider_tool,
                }
            ),
            external_reference_id=job_id,
            started_at=started,
            finished_at=finished,
            duration_ms=int((finished - started).total_seconds() * 1000),
            side_effect_observed=tool.side_effect_class,
            approval_reference=request.approval_reference,
            skill_id=request.skill_id,
            skill_version=request.skill_version,
        )
        return attach_evidence_to_result(result, request=request, tool=tool)

    def _build_mcp_arguments(self, request: ConnectorExecutionRequest) -> dict[str, Any]:
        spec = dict(request.input_payload.get("spec") or request.input_payload)
        return {
            "asset_type": spec.get("asset_type"),
            "style": spec.get("style"),
            "aspect_ratio": spec.get("aspect_ratio"),
            "brand": spec.get("brand"),
            "prompt": spec.get("prompt"),
            "negative_prompt": spec.get("negative_prompt"),
            "references": spec.get("references") or [],
            "model": spec.get("model"),
            "duration_seconds": spec.get("duration_seconds"),
            "metadata": spec.get("metadata") or {},
            **{
                key: value
                for key, value in request.input_payload.items()
                if key not in {"spec"}
            },
        }

    def _blocked(
        self,
        request: ConnectorExecutionRequest,
        tool: ConnectorToolDefinition,
        started: datetime,
        code: str,
    ) -> ConnectorExecutionResult:
        finished = datetime.now(UTC)
        result = ConnectorExecutionResult(
            request_id=request.request_id,
            connector_id=request.connector_id,
            connector_version=request.connector_version,
            tool_id=request.tool_id,
            status=ConnectorExecutionResultStatus.REJECTED_BY_POLICY,
            output_payload={"detail_code": code},
            started_at=started,
            finished_at=finished,
            duration_ms=0,
            skill_id=request.skill_id,
            skill_version=request.skill_version,
        )
        return attach_evidence_to_result(result, request=request, tool=tool)

    def _failed(
        self,
        request: ConnectorExecutionRequest,
        started: datetime,
        code: str,
        *,
        safe_details: dict[str, Any] | None = None,
    ) -> ConnectorExecutionResult:
        from app.connectors.contracts import ConnectorExecutionError

        finished = datetime.now(UTC)
        tool = self._tools.get(request.tool_id)
        result = ConnectorExecutionResult(
            request_id=request.request_id,
            connector_id=request.connector_id,
            connector_version=request.connector_version,
            tool_id=request.tool_id,
            status=ConnectorExecutionResultStatus.FAILED,
            error=ConnectorExecutionError(code=code, message=code, safe_details=safe_details or {}),
            started_at=started,
            finished_at=finished,
            duration_ms=int((finished - started).total_seconds() * 1000),
            skill_id=request.skill_id,
            skill_version=request.skill_version,
        )
        if tool is not None:
            return attach_evidence_to_result(result, request=request, tool=tool)
        return result


def _redact_url(value: str | None) -> str | None:
    if not value:
        return None
    if "?" not in value:
        return value
    base, _query = value.split("?", 1)
    return f"{base}?[REDACTED]"
