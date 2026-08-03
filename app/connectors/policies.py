"""Pure deny-by-default Connector policy evaluation (SKILL-01.5)."""

from __future__ import annotations

from app.connectors.classifications import (
    is_read_only_no_side_effect,
    requires_elevated_approval,
    requires_human_approval,
)
from app.connectors.contracts import (
    ConnectorDataSensitivity,
    ConnectorDescriptor,
    ConnectorExecutionRequest,
    ConnectorHealthState,
    ConnectorPolicyDecision,
    ConnectorPolicyFinding,
    ConnectorPolicyOutcome,
    ConnectorStatus,
    ConnectorToolDefinition,
    ProjectConnectorBinding,
    TenantConnectorBinding,
    payload_contains_secret_like_keys,
)
from app.connectors.fixtures import (
    ADVERTISING_CONNECTOR_ID,
    TELEGRAM_MCP_CONNECTOR_ID,
)

_SELECTABLE_STATUSES = frozenset(
    {
        ConnectorStatus.ACTIVE,
        ConnectorStatus.APPROVED,
        ConnectorStatus.DEGRADED,
    }
)


def _finding(check_id: str, passed: bool, message: str = "") -> ConnectorPolicyFinding:
    return ConnectorPolicyFinding(check_id=check_id, passed=passed, message=message)


def _deny(findings: list[ConnectorPolicyFinding], reason: str) -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.DENY,
        findings=tuple(findings),
        effective_tool_allowed=False,
        approval_required=False,
        reason=reason,
    )


def _require_approval(
    findings: list[ConnectorPolicyFinding], reason: str
) -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.REQUIRE_APPROVAL,
        findings=tuple(findings),
        effective_tool_allowed=False,
        approval_required=True,
        reason=reason,
    )


def _allow(findings: list[ConnectorPolicyFinding]) -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.ALLOW,
        findings=tuple(findings),
        effective_tool_allowed=True,
        approval_required=False,
        reason="allowed",
    )


def _defer(findings: list[ConnectorPolicyFinding], reason: str) -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.DEFER,
        findings=tuple(findings),
        effective_tool_allowed=False,
        approval_required=False,
        reason=reason,
    )


def _unavailable(findings: list[ConnectorPolicyFinding], reason: str) -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.UNAVAILABLE,
        findings=tuple(findings),
        effective_tool_allowed=False,
        approval_required=False,
        reason=reason,
    )


def skill_tool_intersection_allowed(
    skill_allowed_tools: tuple[str, ...],
    tool_id: str,
) -> bool:
    return tool_id in skill_allowed_tools


def evaluate_connector_request(
    request: ConnectorExecutionRequest,
    connector_descriptor: ConnectorDescriptor,
    tool_definition: ConnectorToolDefinition,
    tenant_binding: TenantConnectorBinding | None,
    project_binding: ProjectConnectorBinding | None,
) -> ConnectorPolicyDecision:
    findings: list[ConnectorPolicyFinding] = []

    if connector_descriptor.connector_id != tool_definition.connector_id:
        findings.append(
            _finding("tool_connector_id_match", False, "Tool does not belong to connector.")
        )
        return _deny(findings, "tool_connector_mismatch")

    if connector_descriptor.connector_version != request.connector_version:
        findings.append(_finding("connector_version_match", False, "Connector version mismatch."))
        return _deny(findings, "connector_version_mismatch")

    if connector_descriptor.status == ConnectorStatus.REJECTED:
        findings.append(_finding("connector_status", False, "Connector is rejected."))
        return _deny(findings, "connector_rejected")

    if connector_descriptor.status == ConnectorStatus.ARCHIVED:
        findings.append(_finding("connector_status", False, "Connector is archived."))
        return _deny(findings, "connector_archived")

    if connector_descriptor.status == ConnectorStatus.SUSPENDED:
        findings.append(_finding("connector_status", False, "Connector is suspended."))
        return _deny(findings, "connector_suspended")

    if connector_descriptor.status not in _SELECTABLE_STATUSES:
        findings.append(
            _finding(
                "connector_status",
                False,
                f"Connector status {connector_descriptor.status.value} is not selectable.",
            )
        )
        return _deny(findings, "connector_not_selectable")

    if connector_descriptor.status == ConnectorStatus.DEGRADED:
        if connector_descriptor.health_state == ConnectorHealthState.UNAVAILABLE:
            findings.append(_finding("connector_health", False, "Connector health unavailable."))
            return _unavailable(findings, "connector_health_unavailable")
        findings.append(_finding("connector_health", False, "Connector is degraded."))
        return _defer(findings, "connector_degraded")

    if (
        connector_descriptor.is_mcp
        and connector_descriptor.connector_id == TELEGRAM_MCP_CONNECTOR_ID
    ):
        findings.append(_finding("telegram_mcp_rejected", False, "Telegram MCP is rejected."))
        return _deny(findings, "telegram_mcp_rejected")

    if connector_descriptor.connector_id == ADVERTISING_CONNECTOR_ID:
        findings.append(
            _finding("advertising_spend_denied", False, "Advertising spend denied by default.")
        )
        return _deny(findings, "advertising_spend_denied")

    if not tool_definition.enabled_by_default:
        findings.append(
            _finding("tool_enabled_by_default", True, "Tool is not enabled by default.")
        )

    if tenant_binding is None or not tenant_binding.visible:
        findings.append(_finding("tenant_visibility", False, "Tenant binding is not visible."))
        return _deny(findings, "tenant_invisible")

    if tenant_binding.tenant_id != request.tenant_id:
        findings.append(_finding("tenant_scope", False, "Tenant scope mismatch."))
        return _deny(findings, "tenant_scope_mismatch")

    if project_binding is None:
        findings.append(_finding("project_binding", False, "Project binding missing."))
        return _deny(findings, "project_binding_missing")

    if project_binding.tenant_id != request.tenant_id:
        findings.append(_finding("tenant_scope", False, "Project tenant mismatch."))
        return _deny(findings, "project_tenant_mismatch")

    if project_binding.project_id != request.project_id:
        findings.append(_finding("project_scope", False, "Project scope mismatch."))
        return _deny(findings, "project_scope_mismatch")

    if request.tool_id not in tenant_binding.enabled_tool_ids:
        findings.append(_finding("tenant_tool_allowlist", False, "Tool not in tenant allowlist."))
        return _deny(findings, "tenant_tool_not_allowed")

    if request.tool_id not in project_binding.enabled_tool_ids:
        findings.append(_finding("project_tool_allowlist", False, "Tool not in project allowlist."))
        return _deny(findings, "project_tool_not_allowed")

    skill_allowed = skill_tool_intersection_allowed(request.skill_allowed_tools, request.tool_id)
    findings.append(
        _finding("skill_tool_intersection", skill_allowed, "Skill declared tool permission.")
    )
    if not skill_allowed:
        return _deny(findings, "skill_tool_not_allowed")

    if request.runtime_id not in connector_descriptor.runtime_compatible:
        findings.append(_finding("runtime_compatibility", False, "Runtime incompatible."))
        return _deny(findings, "runtime_incompatible")

    if request.runtime_id not in tenant_binding.runtime_compatible:
        findings.append(
            _finding("tenant_runtime_compatibility", False, "Tenant runtime incompatible.")
        )
        return _deny(findings, "tenant_runtime_incompatible")

    credential_required = (
        tool_definition.data_sensitivity != ConnectorDataSensitivity.PUBLIC
        or tool_definition.billing_sensitive
    )
    if credential_required and request.credential_binding_reference is None:
        findings.append(_finding("credential_binding", False, "Credential binding required."))
        return _deny(findings, "credential_binding_missing")

    if request.credential_binding_reference is not None:
        binding = request.credential_binding_reference
        if binding.tenant_id != request.tenant_id:
            findings.append(
                _finding("credential_tenant_scope", False, "Credential tenant mismatch.")
            )
            return _deny(findings, "credential_tenant_mismatch")
        if binding.connector_id != request.connector_id:
            findings.append(
                _finding("credential_connector_scope", False, "Credential connector mismatch.")
            )
            return _deny(findings, "credential_connector_mismatch")
        if binding.status != "active":
            findings.append(_finding("credential_status", False, "Credential binding not active."))
            return _deny(findings, "credential_not_active")

    secret_key = payload_contains_secret_like_keys(request.input_payload)
    if secret_key:
        findings.append(_finding("input_payload_secrets", False, f"Secret-like key: {secret_key}"))
        return _deny(findings, "input_payload_secret")

    if (
        tool_definition.idempotency.value in {"unknown", "not_idempotent"}
        and request.retry_policy.max_attempts > 1
    ):
        findings.append(
            _finding("idempotency_policy", False, "Non-idempotent tool cannot auto-retry.")
        )
        return _deny(findings, "non_idempotent_retry_denied")

    if tool_definition.billing_sensitive:
        if request.budget_context is None:
            findings.append(_finding("budget_context", False, "Budget context required."))
            return _require_approval(findings, "billing_budget_context_required")
        if (
            request.budget_context.deny_above_limit
            and request.budget_context.request_budget_limit is None
        ):
            findings.append(
                _finding("budget_limit", False, "Unknown billing cost cannot auto-allow.")
            )
            return _require_approval(findings, "billing_cost_unknown")

    if requires_elevated_approval(tool_definition):
        if request.approval_reference is None:
            findings.append(_finding("elevated_approval", False, "Elevated approval required."))
            return _require_approval(findings, "elevated_approval_required")

    elif requires_human_approval(tool_definition):
        if request.approval_reference is None:
            findings.append(_finding("approval_required", False, "Human approval required."))
            return _require_approval(findings, "approval_required")

    elif not is_read_only_no_side_effect(tool_definition):
        findings.append(
            _finding("action_classification", False, "Non-read action requires approval.")
        )
        return _require_approval(findings, "action_requires_approval")

    if (
        tool_definition.publication_sensitive
        and connector_descriptor.is_native_authoritative is False
        and (
            connector_descriptor.primary_class.value != "publication"
            or connector_descriptor.is_mcp
        )
    ):
        findings.append(
            _finding(
                "publication_route",
                False,
                "Publication must route through authoritative native contour.",
            )
        )
        return _deny(findings, "publication_route_invalid")

    if tool_definition.destructive and request.approval_reference is None:
        findings.append(
            _finding("destructive_action", False, "Destructive action requires approval.")
        )
        return _require_approval(findings, "destructive_approval_required")

    if tool_definition.evidence_requirements and not request.evidence_context:
        findings.append(_finding("evidence_requirements", False, "Evidence context required."))
        return _deny(findings, "evidence_context_missing")

    if request.dry_run and not connector_descriptor.adapter.supports_dry_run:
        findings.append(
            _finding("dry_run_compatibility", True, "Dry-run not supported by adapter.")
        )

    findings.append(_finding("policy_complete", True, "All policy checks passed."))
    return _allow(findings)
