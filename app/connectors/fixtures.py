"""Synthetic test fixtures for Connector Gateway (SKILL-01.5)."""

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

RESEARCH_CONNECTOR_ID = "fixture.connector.research_read"
CONTENT_GEN_CONNECTOR_ID = "fixture.connector.content_generation"
PUBLICATION_CONNECTOR_ID = "fixture.connector.publication"
ADVERTISING_CONNECTOR_ID = "fixture.connector.advertising"
NATIVE_TELEGRAM_CONNECTOR_ID = "connector.native.telegram_publication"
TELEGRAM_MCP_CONNECTOR_ID = "fixture.connector.telegram_mcp_rejected"

RESEARCH_TOOL_ID = "research.read"
CONTENT_GEN_TOOL_ID = "content.generate"
PUBLICATION_TOOL_ID = "publication.publish"
ADVERTISING_TOOL_ID = "advertising.spend"
NATIVE_TELEGRAM_TOOL_ID = "telegram.publish_native"
TELEGRAM_MCP_TOOL_ID = "telegram.mcp_send"

CONNECTOR_VERSION = "0.1.0-fixture"


def research_read_tool() -> ConnectorToolDefinition:
    return ConnectorToolDefinition(
        connector_id=RESEARCH_CONNECTOR_ID,
        tool_id=RESEARCH_TOOL_ID,
        name="Research Read",
        description="Synthetic read-only research tool (fixture).",
        action_type=ConnectorActionType.READ,
        side_effect_class=ConnectorSideEffectClass.NONE,
        data_sensitivity=ConnectorDataSensitivity.PUBLIC,
        approval_class=ConnectorApprovalClass.NONE,
        billing_sensitive=False,
        publication_sensitive=False,
        destructive=False,
        idempotency=ConnectorIdempotencyClass.GUARANTEED,
        enabled_by_default=False,
    )


def content_generation_tool() -> ConnectorToolDefinition:
    return ConnectorToolDefinition(
        connector_id=CONTENT_GEN_CONNECTOR_ID,
        tool_id=CONTENT_GEN_TOOL_ID,
        name="Content Generate",
        description="Synthetic billing-sensitive content generation tool (fixture).",
        action_type=ConnectorActionType.EXECUTE,
        side_effect_class=ConnectorSideEffectClass.REVERSIBLE,
        data_sensitivity=ConnectorDataSensitivity.TENANT_INTERNAL,
        approval_class=ConnectorApprovalClass.OWNER_APPROVAL,
        billing_sensitive=True,
        publication_sensitive=False,
        destructive=False,
        idempotency=ConnectorIdempotencyClass.UNKNOWN,
        enabled_by_default=False,
    )


def publication_tool() -> ConnectorToolDefinition:
    return ConnectorToolDefinition(
        connector_id=PUBLICATION_CONNECTOR_ID,
        tool_id=PUBLICATION_TOOL_ID,
        name="Publication Publish",
        description="Synthetic externally visible publication tool (fixture).",
        action_type=ConnectorActionType.PUBLISH,
        side_effect_class=ConnectorSideEffectClass.EXTERNALLY_VISIBLE,
        data_sensitivity=ConnectorDataSensitivity.TENANT_INTERNAL,
        approval_class=ConnectorApprovalClass.OWNER_APPROVAL,
        billing_sensitive=False,
        publication_sensitive=True,
        destructive=False,
        idempotency=ConnectorIdempotencyClass.NOT_IDEMPOTENT,
        enabled_by_default=False,
    )


def advertising_spend_tool() -> ConnectorToolDefinition:
    return ConnectorToolDefinition(
        connector_id=ADVERTISING_CONNECTOR_ID,
        tool_id=ADVERTISING_TOOL_ID,
        name="Advertising Spend",
        description="Synthetic advertising spend tool denied by default policy (fixture).",
        action_type=ConnectorActionType.BILLING,
        side_effect_class=ConnectorSideEffectClass.FINANCIALLY_SENSITIVE,
        data_sensitivity=ConnectorDataSensitivity.CONFIDENTIAL,
        approval_class=ConnectorApprovalClass.ELEVATED_APPROVAL,
        billing_sensitive=True,
        publication_sensitive=False,
        destructive=False,
        idempotency=ConnectorIdempotencyClass.UNKNOWN,
        enabled_by_default=False,
    )


def native_telegram_tool() -> ConnectorToolDefinition:
    return ConnectorToolDefinition(
        connector_id=NATIVE_TELEGRAM_CONNECTOR_ID,
        tool_id=NATIVE_TELEGRAM_TOOL_ID,
        name="Native Telegram Publish",
        description="Authoritative native Telegram publication boundary metadata (not MCP).",
        action_type=ConnectorActionType.PUBLISH,
        side_effect_class=ConnectorSideEffectClass.EXTERNALLY_VISIBLE,
        data_sensitivity=ConnectorDataSensitivity.TENANT_INTERNAL,
        approval_class=ConnectorApprovalClass.OWNER_APPROVAL,
        billing_sensitive=False,
        publication_sensitive=True,
        destructive=False,
        idempotency=ConnectorIdempotencyClass.NOT_IDEMPOTENT,
        enabled_by_default=False,
    )


def telegram_mcp_tool() -> ConnectorToolDefinition:
    return ConnectorToolDefinition(
        connector_id=TELEGRAM_MCP_CONNECTOR_ID,
        tool_id=TELEGRAM_MCP_TOOL_ID,
        name="Telegram MCP Send",
        description="Rejected Telegram MCP fixture.",
        action_type=ConnectorActionType.PUBLISH,
        side_effect_class=ConnectorSideEffectClass.EXTERNALLY_VISIBLE,
        data_sensitivity=ConnectorDataSensitivity.TENANT_INTERNAL,
        approval_class=ConnectorApprovalClass.OWNER_APPROVAL,
        billing_sensitive=False,
        publication_sensitive=True,
        destructive=False,
        idempotency=ConnectorIdempotencyClass.UNKNOWN,
        enabled_by_default=False,
    )


def research_read_descriptor(
    *, status: ConnectorStatus = ConnectorStatus.ACTIVE
) -> ConnectorDescriptor:
    return ConnectorDescriptor(
        connector_id=RESEARCH_CONNECTOR_ID,
        connector_version=CONNECTOR_VERSION,
        name="Fixture Research Read Connector",
        status=status,
        primary_class=ConnectorClass.RESEARCH,
        adapter=ConnectorAdapterDescriptor(
            adapter_id="synthetic.research", adapter_kind="synthetic"
        ),
        health_state=ConnectorHealthState.HEALTHY,
        fixture_only=True,
    )


def content_generation_descriptor(
    *, status: ConnectorStatus = ConnectorStatus.ACTIVE
) -> ConnectorDescriptor:
    return ConnectorDescriptor(
        connector_id=CONTENT_GEN_CONNECTOR_ID,
        connector_version=CONNECTOR_VERSION,
        name="Fixture Content Generation Connector",
        status=status,
        primary_class=ConnectorClass.CONTENT_GENERATION,
        adapter=ConnectorAdapterDescriptor(
            adapter_id="synthetic.content", adapter_kind="synthetic"
        ),
        health_state=ConnectorHealthState.HEALTHY,
        fixture_only=True,
    )


def publication_descriptor(
    *, status: ConnectorStatus = ConnectorStatus.ACTIVE
) -> ConnectorDescriptor:
    return ConnectorDescriptor(
        connector_id=PUBLICATION_CONNECTOR_ID,
        connector_version=CONNECTOR_VERSION,
        name="Fixture Publication Connector",
        status=status,
        primary_class=ConnectorClass.PUBLICATION,
        adapter=ConnectorAdapterDescriptor(
            adapter_id="synthetic.publication", adapter_kind="synthetic"
        ),
        health_state=ConnectorHealthState.HEALTHY,
        fixture_only=True,
    )


def advertising_descriptor(
    *, status: ConnectorStatus = ConnectorStatus.ACTIVE
) -> ConnectorDescriptor:
    return ConnectorDescriptor(
        connector_id=ADVERTISING_CONNECTOR_ID,
        connector_version=CONNECTOR_VERSION,
        name="Fixture Advertising Connector",
        status=status,
        primary_class=ConnectorClass.ADVERTISING,
        adapter=ConnectorAdapterDescriptor(
            adapter_id="synthetic.advertising", adapter_kind="synthetic"
        ),
        health_state=ConnectorHealthState.HEALTHY,
        fixture_only=True,
    )


def native_telegram_descriptor(
    *, status: ConnectorStatus = ConnectorStatus.ACTIVE
) -> ConnectorDescriptor:
    return ConnectorDescriptor(
        connector_id=NATIVE_TELEGRAM_CONNECTOR_ID,
        connector_version=CONNECTOR_VERSION,
        name="Native Telegram Publication Boundary",
        status=status,
        primary_class=ConnectorClass.PUBLICATION,
        adapter=ConnectorAdapterDescriptor(adapter_id="native.telegram", adapter_kind="native"),
        health_state=ConnectorHealthState.HEALTHY,
        is_mcp=False,
        is_native_authoritative=True,
        fixture_only=False,
    )


def telegram_mcp_descriptor(
    *, status: ConnectorStatus = ConnectorStatus.REJECTED
) -> ConnectorDescriptor:
    return ConnectorDescriptor(
        connector_id=TELEGRAM_MCP_CONNECTOR_ID,
        connector_version=CONNECTOR_VERSION,
        name="Rejected Telegram MCP Fixture",
        status=status,
        primary_class=ConnectorClass.PUBLICATION,
        adapter=ConnectorAdapterDescriptor(
            adapter_id="mcp.telegram.rejected", adapter_kind="mcp_derived"
        ),
        health_state=ConnectorHealthState.UNAVAILABLE,
        is_mcp=True,
        is_native_authoritative=False,
        fixture_only=True,
    )


def all_fixture_tools() -> dict[str, ConnectorToolDefinition]:
    tools = [
        research_read_tool(),
        content_generation_tool(),
        publication_tool(),
        advertising_spend_tool(),
        native_telegram_tool(),
        telegram_mcp_tool(),
    ]
    return {tool.tool_id: tool for tool in tools}


def all_fixture_descriptors() -> dict[str, ConnectorDescriptor]:
    descriptors = [
        research_read_descriptor(),
        content_generation_descriptor(),
        publication_descriptor(),
        advertising_descriptor(),
        native_telegram_descriptor(),
        telegram_mcp_descriptor(),
    ]
    return {descriptor.connector_id: descriptor for descriptor in descriptors}
