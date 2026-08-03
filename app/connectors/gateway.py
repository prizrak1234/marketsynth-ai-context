"""Connector Gateway skeleton — policy harness with synthetic adapter support (SKILL-01.5)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.connectors.adapters import ConnectorAdapterProtocol, SyntheticConnectorAdapter
from app.connectors.contracts import (
    ConnectorDescriptor,
    ConnectorExecutionRequest,
    ConnectorExecutionResult,
    ConnectorExecutionResultStatus,
    ConnectorPolicyOutcome,
    ConnectorToolDefinition,
    ProjectConnectorBinding,
    TenantConnectorBinding,
)
from app.connectors.errors import (
    ConnectorNotFoundError,
    ConnectorToolNotFoundError,
    ConnectorVersionNotFoundError,
)
from app.connectors.evidence import attach_evidence_to_result, redact_provider_metadata
from app.connectors.policies import evaluate_connector_request


class ConnectorGateway:
    """Non-production gateway: policy evaluation and synthetic adapter invocation only."""

    def __init__(
        self,
        *,
        descriptors: dict[str, ConnectorDescriptor],
        tools: dict[str, ConnectorToolDefinition],
        adapters: dict[str, ConnectorAdapterProtocol] | None = None,
    ) -> None:
        self._descriptors = descriptors
        self._tools = tools
        self._adapters = adapters or {}

    def resolve_descriptor(self, connector_id: str, connector_version: str) -> ConnectorDescriptor:
        descriptor = self._descriptors.get(connector_id)
        if descriptor is None:
            raise ConnectorNotFoundError()
        if descriptor.connector_version != connector_version:
            raise ConnectorVersionNotFoundError()
        return descriptor

    def resolve_tool(self, connector_id: str, tool_id: str) -> ConnectorToolDefinition:
        tool = self._tools.get(tool_id)
        if tool is None or tool.connector_id != connector_id:
            raise ConnectorToolNotFoundError()
        return tool

    def evaluate_policy(
        self,
        request: ConnectorExecutionRequest,
        *,
        tenant_binding: TenantConnectorBinding | None,
        project_binding: ProjectConnectorBinding | None,
    ) -> tuple[ConnectorDescriptor, ConnectorToolDefinition, object]:
        descriptor = self.resolve_descriptor(request.connector_id, request.connector_version)
        tool = self.resolve_tool(request.connector_id, request.tool_id)
        decision = evaluate_connector_request(
            request,
            descriptor,
            tool,
            tenant_binding,
            project_binding,
        )
        return descriptor, tool, decision

    def execute(
        self,
        request: ConnectorExecutionRequest,
        *,
        tenant_binding: TenantConnectorBinding | None,
        project_binding: ProjectConnectorBinding | None,
    ) -> ConnectorExecutionResult:
        started = datetime.now(UTC)
        descriptor, tool, decision = self.evaluate_policy(
            request,
            tenant_binding=tenant_binding,
            project_binding=project_binding,
        )
        finished = datetime.now(UTC)

        if decision.outcome == ConnectorPolicyOutcome.DENY:
            result = ConnectorExecutionResult(
                request_id=request.request_id,
                connector_id=request.connector_id,
                connector_version=request.connector_version,
                tool_id=request.tool_id,
                status=ConnectorExecutionResultStatus.REJECTED_BY_POLICY,
                started_at=started,
                finished_at=finished,
                duration_ms=0,
                skill_id=request.skill_id,
                skill_version=request.skill_version,
            )
            return attach_evidence_to_result(result, request=request, tool=tool)

        if decision.outcome in {
            ConnectorPolicyOutcome.REQUIRE_APPROVAL,
            ConnectorPolicyOutcome.REQUIRE_ADDITIONAL_CONTEXT,
        }:
            result = ConnectorExecutionResult(
                request_id=request.request_id,
                connector_id=request.connector_id,
                connector_version=request.connector_version,
                tool_id=request.tool_id,
                status=ConnectorExecutionResultStatus.APPROVAL_REQUIRED,
                started_at=started,
                finished_at=finished,
                duration_ms=0,
                skill_id=request.skill_id,
                skill_version=request.skill_version,
            )
            return attach_evidence_to_result(result, request=request, tool=tool)

        if decision.outcome in {ConnectorPolicyOutcome.DEFER, ConnectorPolicyOutcome.UNAVAILABLE}:
            status = (
                ConnectorExecutionResultStatus.UNAVAILABLE
                if decision.outcome == ConnectorPolicyOutcome.UNAVAILABLE
                else ConnectorExecutionResultStatus.UNKNOWN_OUTCOME
            )
            result = ConnectorExecutionResult(
                request_id=request.request_id,
                connector_id=request.connector_id,
                connector_version=request.connector_version,
                tool_id=request.tool_id,
                status=status,
                started_at=started,
                finished_at=finished,
                duration_ms=0,
                skill_id=request.skill_id,
                skill_version=request.skill_version,
            )
            return attach_evidence_to_result(result, request=request, tool=tool)

        adapter = self._adapters.get(descriptor.connector_id)
        if adapter is None:
            result = ConnectorExecutionResult(
                request_id=request.request_id,
                connector_id=request.connector_id,
                connector_version=request.connector_version,
                tool_id=request.tool_id,
                status=ConnectorExecutionResultStatus.UNAVAILABLE,
                started_at=started,
                finished_at=finished,
                duration_ms=0,
                skill_id=request.skill_id,
                skill_version=request.skill_version,
            )
            return attach_evidence_to_result(result, request=request, tool=tool)

        raw_result = adapter.execute_tool(request)
        normalized = self.normalize_result(raw_result, request=request, tool=tool)
        return normalized

    def normalize_result(
        self,
        result: ConnectorExecutionResult,
        *,
        request: ConnectorExecutionRequest,
        tool: ConnectorToolDefinition,
    ) -> ConnectorExecutionResult:
        safe_metadata = redact_provider_metadata(result.safe_provider_metadata)
        normalized = result.model_copy(
            update={
                "safe_provider_metadata": safe_metadata,
                "skill_id": request.skill_id,
                "skill_version": request.skill_version,
            }
        )
        if normalized.evidence_descriptor is None:
            normalized = attach_evidence_to_result(normalized, request=request, tool=tool)
        return normalized


def build_test_gateway() -> tuple[ConnectorGateway, dict[str, SyntheticConnectorAdapter]]:
    from app.connectors.fixtures import (
        all_fixture_descriptors,
        all_fixture_tools,
        content_generation_descriptor,
        content_generation_tool,
        publication_descriptor,
        publication_tool,
        research_read_descriptor,
        research_read_tool,
    )

    descriptors = all_fixture_descriptors()
    tools = all_fixture_tools()
    adapters: dict[str, SyntheticConnectorAdapter] = {
        research_read_descriptor().connector_id: SyntheticConnectorAdapter(
            research_read_descriptor(),
            (research_read_tool(),),
        ),
        content_generation_descriptor().connector_id: SyntheticConnectorAdapter(
            content_generation_descriptor(),
            (content_generation_tool(),),
        ),
        publication_descriptor().connector_id: SyntheticConnectorAdapter(
            publication_descriptor(),
            (publication_tool(),),
        ),
    }
    gateway = ConnectorGateway(descriptors=descriptors, tools=tools, adapters=adapters)
    return gateway, adapters
