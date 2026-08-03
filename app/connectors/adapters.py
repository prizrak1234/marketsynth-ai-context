"""Connector adapter protocol and synthetic in-memory adapter (SKILL-01.5)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
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


class ConnectorAdapterProtocol(Protocol):
    def describe_connector(self) -> ConnectorDescriptor: ...

    def list_tools(self) -> tuple[ConnectorToolDefinition, ...]: ...

    def validate_configuration(self) -> tuple[str, ...]: ...

    def health_check(self) -> ConnectorHealthState: ...

    def execute_tool(self, request: ConnectorExecutionRequest) -> ConnectorExecutionResult: ...


class SyntheticConnectorAdapter:
    """In-memory test adapter only — no network, no SDK, no credentials."""

    def __init__(
        self,
        descriptor: ConnectorDescriptor,
        tools: tuple[ConnectorToolDefinition, ...],
    ) -> None:
        self._descriptor = descriptor
        self._tools = tools
        self.invocation_count = 0
        self.last_request: ConnectorExecutionRequest | None = None

    def describe_connector(self) -> ConnectorDescriptor:
        return self._descriptor

    def list_tools(self) -> tuple[ConnectorToolDefinition, ...]:
        return self._tools

    def validate_configuration(self) -> tuple[str, ...]:
        return ()

    def health_check(self) -> ConnectorHealthState:
        return ConnectorHealthState.HEALTHY

    def execute_tool(self, request: ConnectorExecutionRequest) -> ConnectorExecutionResult:
        self.invocation_count += 1
        self.last_request = request
        started = datetime.now(UTC)
        finished = started
        tool = next((item for item in self._tools if item.tool_id == request.tool_id), None)
        if tool is None:
            return ConnectorExecutionResult(
                request_id=request.request_id,
                connector_id=request.connector_id,
                connector_version=request.connector_version,
                tool_id=request.tool_id,
                status=ConnectorExecutionResultStatus.FAILED,
                started_at=started,
                finished_at=finished,
                duration_ms=0,
                skill_id=request.skill_id,
                skill_version=request.skill_version,
            )

        output = {"synthetic": True, "tool_id": request.tool_id}
        metadata = {"provider": "synthetic", "request_echo": request.tool_id}
        result = ConnectorExecutionResult(
            request_id=request.request_id,
            connector_id=request.connector_id,
            connector_version=request.connector_version,
            tool_id=request.tool_id,
            status=ConnectorExecutionResultStatus.SUCCEEDED,
            output_payload=output,
            safe_provider_metadata=redact_provider_metadata(metadata),
            external_reference_id=str(uuid4()),
            idempotency_observed=request.idempotency_key is not None,
            started_at=started,
            finished_at=finished,
            duration_ms=0,
            side_effect_observed=tool.side_effect_class,
            approval_reference=request.approval_reference,
            skill_id=request.skill_id,
            skill_version=request.skill_version,
        )
        return attach_evidence_to_result(result, request=request, tool=tool)


class ProductionConnectorAdapterStub:
    """Production placeholder — real invocation is intentionally not implemented."""

    def __init__(self, descriptor: ConnectorDescriptor) -> None:
        self._descriptor = descriptor

    def describe_connector(self) -> ConnectorDescriptor:
        return self._descriptor

    def list_tools(self) -> tuple[ConnectorToolDefinition, ...]:
        raise NotImplementedError("Production connector adapter is not implemented in SKILL-01.5.")

    def validate_configuration(self) -> tuple[str, ...]:
        raise NotImplementedError("Production connector adapter is not implemented in SKILL-01.5.")

    def health_check(self) -> ConnectorHealthState:
        return ConnectorHealthState.UNKNOWN

    def execute_tool(self, request: ConnectorExecutionRequest) -> ConnectorExecutionResult:
        raise NotImplementedError("Production connector adapter is not implemented in SKILL-01.5.")
