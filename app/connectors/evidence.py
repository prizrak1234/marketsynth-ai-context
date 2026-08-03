"""Evidence descriptor helpers for Connector Gateway (SKILL-01.5)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.connectors.contracts import (
    ConnectorEvidenceDescriptor,
    ConnectorExecutionRequest,
    ConnectorExecutionResult,
    ConnectorExecutionResultStatus,
    ConnectorToolDefinition,
)


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))


def hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def redact_provider_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    secret_fragments = ("token", "secret", "password", "api_key", "authorization", "credential")
    for key, value in metadata.items():
        lowered = key.lower()
        if any(fragment in lowered for fragment in secret_fragments):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_provider_metadata(value)
        else:
            redacted[key] = value
    return redacted


def build_evidence_descriptor(
    *,
    request: ConnectorExecutionRequest,
    tool: ConnectorToolDefinition,
    result_status: ConnectorExecutionResultStatus,
    output_payload: dict[str, Any],
    safe_provider_metadata: dict[str, Any],
    started_at: datetime,
    finished_at: datetime,
    external_reference_id: str | None = None,
    cost_observed: float | None = None,
    lineage_parent_ids: tuple[str, ...] = (),
    evidence_id: UUID | None = None,
) -> ConnectorEvidenceDescriptor:
    return ConnectorEvidenceDescriptor(
        evidence_id=evidence_id or uuid4(),
        request_id=request.request_id,
        connector_id=request.connector_id,
        connector_version=request.connector_version,
        tool_id=request.tool_id,
        skill_id=request.skill_id,
        skill_version=request.skill_version,
        tenant_id=request.tenant_id,
        project_id=request.project_id,
        action_type=tool.action_type,
        side_effect_class=tool.side_effect_class,
        approval_reference=request.approval_reference,
        external_reference_id=external_reference_id,
        input_hash=hash_payload(request.input_payload),
        output_hash=hash_payload(output_payload),
        provider_metadata_hash=hash_payload(safe_provider_metadata),
        cost_observed=cost_observed,
        started_at=started_at,
        finished_at=finished_at,
        result_status=result_status,
        lineage_parent_ids=lineage_parent_ids,
    )


def attach_evidence_to_result(
    result: ConnectorExecutionResult,
    *,
    request: ConnectorExecutionRequest,
    tool: ConnectorToolDefinition,
) -> ConnectorExecutionResult:
    evidence = build_evidence_descriptor(
        request=request,
        tool=tool,
        result_status=result.status,
        output_payload=result.output_payload,
        safe_provider_metadata=result.safe_provider_metadata,
        started_at=result.started_at,
        finished_at=result.finished_at,
        external_reference_id=result.external_reference_id,
        cost_observed=result.cost_observed,
    )
    return result.model_copy(update={"evidence_descriptor": evidence})
