"""Higgsfield connector descriptor and tool definitions (CONN-HF-01.1)."""

from __future__ import annotations

from app.connectors.contracts import (
    ConnectorActionType,
    ConnectorAdapterDescriptor,
    ConnectorApprovalClass,
    ConnectorClass,
    ConnectorDataSensitivity,
    ConnectorDescriptor,
    ConnectorHealthState,
    ConnectorIdempotencyClass,
    ConnectorSideEffectClass,
    ConnectorStatus,
    ConnectorToolDefinition,
)
from app.connectors.higgsfield.constants import (
    HIGGSFIELD_CONNECTOR_ID,
    HIGGSFIELD_CONNECTOR_VERSION,
    MEDIA_OP_ASSET_FETCH,
    MEDIA_OP_IMAGE_GENERATE,
    MEDIA_OP_JOB_GET_STATUS,
    MEDIA_OP_VIDEO_GENERATE,
)
from app.connectors.higgsfield.sandbox.operation_mapping import load_operation_mapping
from app.core.config import Settings


def _render_tool(
    *,
    tool_id: str,
    name: str,
    description: str,
    action_type: ConnectorActionType = ConnectorActionType.EXECUTE,
) -> ConnectorToolDefinition:
    return ConnectorToolDefinition(
        connector_id=HIGGSFIELD_CONNECTOR_ID,
        tool_id=tool_id,
        name=name,
        description=description,
        input_schema_reference="app/schemas/contracts.py#MediaRenderSpec",
        action_type=action_type,
        side_effect_class=ConnectorSideEffectClass.REVERSIBLE,
        data_sensitivity=ConnectorDataSensitivity.TENANT_INTERNAL,
        approval_class=ConnectorApprovalClass.OWNER_APPROVAL,
        billing_sensitive=True,
        publication_sensitive=False,
        destructive=False,
        idempotency=ConnectorIdempotencyClass.UNKNOWN,
        evidence_requirements=("render_spec_hash", "provider_job_id"),
        enabled_by_default=False,
    )


def media_image_generate_tool() -> ConnectorToolDefinition:
    return _render_tool(
        tool_id=MEDIA_OP_IMAGE_GENERATE,
        name="Generate Image",
        description="Execute a fully-specified image render via verified Higgsfield MCP tool.",
    )


def media_video_generate_tool() -> ConnectorToolDefinition:
    return _render_tool(
        tool_id=MEDIA_OP_VIDEO_GENERATE,
        name="Generate Video",
        description="Execute a fully-specified video render via verified Higgsfield MCP tool.",
    )


def media_job_get_status_tool() -> ConnectorToolDefinition:
    return ConnectorToolDefinition(
        connector_id=HIGGSFIELD_CONNECTOR_ID,
        tool_id=MEDIA_OP_JOB_GET_STATUS,
        name="Get Job Status",
        description="Poll async provider generation job status.",
        action_type=ConnectorActionType.READ,
        side_effect_class=ConnectorSideEffectClass.NONE,
        data_sensitivity=ConnectorDataSensitivity.TENANT_INTERNAL,
        approval_class=ConnectorApprovalClass.NONE,
        billing_sensitive=False,
        publication_sensitive=False,
        destructive=False,
        idempotency=ConnectorIdempotencyClass.GUARANTEED,
        enabled_by_default=False,
    )


def media_asset_fetch_tool() -> ConnectorToolDefinition:
    return ConnectorToolDefinition(
        connector_id=HIGGSFIELD_CONNECTOR_ID,
        tool_id=MEDIA_OP_ASSET_FETCH,
        name="Fetch Render Asset",
        description="Fetch completed render artifact metadata/URL from provider.",
        action_type=ConnectorActionType.READ,
        side_effect_class=ConnectorSideEffectClass.NONE,
        data_sensitivity=ConnectorDataSensitivity.TENANT_INTERNAL,
        approval_class=ConnectorApprovalClass.NONE,
        billing_sensitive=False,
        publication_sensitive=False,
        destructive=False,
        idempotency=ConnectorIdempotencyClass.GUARANTEED,
        enabled_by_default=False,
    )


def all_higgsfield_tools() -> dict[str, ConnectorToolDefinition]:
    tools = [
        media_image_generate_tool(),
        media_video_generate_tool(),
        media_job_get_status_tool(),
        media_asset_fetch_tool(),
    ]
    return {tool.tool_id: tool for tool in tools}


def higgsfield_descriptor(settings: Settings | None = None) -> ConnectorDescriptor:
    from app.core.config import get_settings

    s = settings or get_settings()
    mapping = load_operation_mapping()
    sandbox_verified = mapping.sandbox_verified()

    if not s.higgsfield_mcp_enabled or not sandbox_verified:
        status = ConnectorStatus.QUARANTINED
        health = ConnectorHealthState.UNAVAILABLE
    elif not s.higgsfield_mcp_configured:
        status = ConnectorStatus.APPROVED
        health = ConnectorHealthState.DEGRADED
    else:
        status = ConnectorStatus.APPROVED
        health = ConnectorHealthState.DEGRADED

    return ConnectorDescriptor(
        connector_id=HIGGSFIELD_CONNECTOR_ID,
        connector_version=HIGGSFIELD_CONNECTOR_VERSION,
        name="Higgsfield MCP Media Renderer",
        description=(
            "Executor-only MCP adapter candidate for image/video rendering. "
            "Sandbox verification required before live customer calls."
        ),
        status=status,
        primary_class=ConnectorClass.CONTENT_GENERATION,
        adapter=ConnectorAdapterDescriptor(
            adapter_id="mcp.higgsfield",
            adapter_kind="mcp_derived",
            version=HIGGSFIELD_CONNECTOR_VERSION,
            supports_dry_run=False,
        ),
        health_state=health,
        is_mcp=True,
        is_native_authoritative=False,
        fixture_only=False,
        runtime_compatible=("operator_sandbox", "media_renderer"),
    )
