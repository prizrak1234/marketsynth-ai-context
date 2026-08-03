"""Centralized severity and blocking rules (SKILL-01.6)."""

from __future__ import annotations

from app.audit.contracts import (
    AuditFinding,
    AuditFindingCategory,
    AuditFindingSeverity,
    AuditOverallSeverity,
    AuditSourceSystem,
)
from app.connectors.contracts import ConnectorPolicyOutcome
from app.skills.quarantine_contracts import QuarantineStaticFindingSeverity
from app.skills.validation_contracts import SkillValidationSeverity

SEVERITY_ORDER: tuple[AuditFindingSeverity, ...] = (
    AuditFindingSeverity.INFO,
    AuditFindingSeverity.WARNING,
    AuditFindingSeverity.ERROR,
    AuditFindingSeverity.CRITICAL,
)

OVERALL_SEVERITY_ORDER: tuple[AuditOverallSeverity, ...] = (
    AuditOverallSeverity.NONE,
    AuditOverallSeverity.INFO,
    AuditOverallSeverity.WARNING,
    AuditOverallSeverity.ERROR,
    AuditOverallSeverity.CRITICAL,
)

_PACKAGE_VALIDATOR_SEVERITY: dict[SkillValidationSeverity, AuditFindingSeverity] = {
    SkillValidationSeverity.INFO: AuditFindingSeverity.INFO,
    SkillValidationSeverity.WARNING: AuditFindingSeverity.WARNING,
    SkillValidationSeverity.ERROR: AuditFindingSeverity.ERROR,
}

_QUARANTINE_STATIC_SEVERITY: dict[QuarantineStaticFindingSeverity, AuditFindingSeverity] = {
    QuarantineStaticFindingSeverity.INFO: AuditFindingSeverity.INFO,
    QuarantineStaticFindingSeverity.WARNING: AuditFindingSeverity.WARNING,
    QuarantineStaticFindingSeverity.ERROR: AuditFindingSeverity.ERROR,
}

_REGISTRY_CONFLICT_SEVERITY: dict[str, AuditFindingSeverity] = {
    "info": AuditFindingSeverity.INFO,
    "warning": AuditFindingSeverity.WARNING,
    "error": AuditFindingSeverity.ERROR,
    "critical": AuditFindingSeverity.CRITICAL,
}

_CONNECTOR_POLICY_REASON_SEVERITY: dict[str, AuditFindingSeverity] = {
    "allowed": AuditFindingSeverity.INFO,
    "approval_required": AuditFindingSeverity.INFO,
    "elevated_approval_required": AuditFindingSeverity.WARNING,
    "billing_budget_context_required": AuditFindingSeverity.ERROR,
    "billing_cost_unknown": AuditFindingSeverity.ERROR,
    "connector_degraded": AuditFindingSeverity.WARNING,
    "connector_health_unavailable": AuditFindingSeverity.WARNING,
    "connector_not_selectable": AuditFindingSeverity.ERROR,
    "credential_binding_missing": AuditFindingSeverity.ERROR,
    "credential_not_active": AuditFindingSeverity.ERROR,
    "destructive_approval_required": AuditFindingSeverity.WARNING,
    "evidence_context_missing": AuditFindingSeverity.ERROR,
    "input_payload_secret": AuditFindingSeverity.CRITICAL,
    "non_idempotent_retry_denied": AuditFindingSeverity.ERROR,
    "project_binding_missing": AuditFindingSeverity.ERROR,
    "publication_route_invalid": AuditFindingSeverity.ERROR,
    "skill_tool_not_allowed": AuditFindingSeverity.ERROR,
    "telegram_mcp_rejected": AuditFindingSeverity.CRITICAL,
    "tenant_invisible": AuditFindingSeverity.CRITICAL,
    "tenant_scope_mismatch": AuditFindingSeverity.CRITICAL,
    "advertising_spend_denied": AuditFindingSeverity.ERROR,
}

_MALICIOUS_QUARANTINE_CODES = frozenset(
    {
        "symlink_escape",
        "path_traversal",
        "executable_payload",
        "secret_file",
        "binary_payload",
    }
)

BLOCKING_SOURCE_CODES = frozenset(
    {
        "security_secret_detected",
        "security_path_traversal",
        "security_symlink_escape",
        "security_executable_payload",
        "manifest_invalid",
        "schema_invalid",
        "identity_conflict",
        "hash_conflict",
        "source_identity_conflict",
        "provenance_missing",
        "cross_tenant_exposure",
        "lifecycle_conflict",
        "connector_policy_deny",
        "billing_without_budget",
        "publication_bypass",
        "tool_not_allowed",
        "network_access_forbidden",
        "input_payload_secret",
        "telegram_mcp_rejected",
        "tenant_invisible",
        "tenant_scope_mismatch",
        "symlink_escape",
        "path_traversal",
        "executable_payload",
        "secret_file",
    }
)

EXECUTION_BLOCKING_SOURCE_CODES = frozenset(
    {
        *BLOCKING_SOURCE_CODES,
        "approval_required",
        "elevated_approval_required",
        "billing_budget_context_required",
        "destructive_approval_required",
    }
)


def map_package_validator_severity(severity: SkillValidationSeverity) -> AuditFindingSeverity:
    return _PACKAGE_VALIDATOR_SEVERITY[severity]


def map_quarantine_static_severity(
    severity: QuarantineStaticFindingSeverity,
) -> AuditFindingSeverity:
    mapped = _QUARANTINE_STATIC_SEVERITY[severity]
    return mapped


def map_quarantine_static_code_severity(
    code: str, severity: QuarantineStaticFindingSeverity
) -> AuditFindingSeverity:
    if code in _MALICIOUS_QUARANTINE_CODES:
        return (
            AuditFindingSeverity.CRITICAL
            if code in {"symlink_escape", "secret_file"}
            else AuditFindingSeverity.ERROR
        )
    return map_quarantine_static_severity(severity)


def map_registry_conflict_severity(severity: str) -> AuditFindingSeverity:
    return _REGISTRY_CONFLICT_SEVERITY.get(severity.lower(), AuditFindingSeverity.ERROR)


def map_connector_policy_outcome(
    outcome: ConnectorPolicyOutcome,
    reason: str,
) -> AuditFindingSeverity:
    if reason in _CONNECTOR_POLICY_REASON_SEVERITY:
        return _CONNECTOR_POLICY_REASON_SEVERITY[reason]
    if outcome == ConnectorPolicyOutcome.DENY:
        if "tenant" in reason or "secret" in reason:
            return AuditFindingSeverity.CRITICAL
        return AuditFindingSeverity.ERROR
    if outcome == ConnectorPolicyOutcome.REQUIRE_APPROVAL:
        return AuditFindingSeverity.INFO
    if outcome in {ConnectorPolicyOutcome.DEFER, ConnectorPolicyOutcome.UNAVAILABLE}:
        return AuditFindingSeverity.WARNING
    if outcome == ConnectorPolicyOutcome.ALLOW:
        return AuditFindingSeverity.INFO
    return AuditFindingSeverity.WARNING


def map_package_validator_code_category(code: str) -> AuditFindingCategory:
    if code.startswith("security_"):
        return AuditFindingCategory.SECURITY
    if code.startswith("schema_"):
        return AuditFindingCategory.SCHEMA
    if code.startswith("manifest_"):
        return AuditFindingCategory.STRUCTURE
    if code.startswith("provenance_"):
        return AuditFindingCategory.PROVENANCE
    if code.startswith("license_"):
        return AuditFindingCategory.LICENSING
    if code.startswith("permission_"):
        return AuditFindingCategory.PERMISSIONS
    if "network" in code:
        return AuditFindingCategory.SECURITY
    return AuditFindingCategory.UNKNOWN


def is_blocking_source_code(source_code: str) -> bool:
    return source_code in BLOCKING_SOURCE_CODES


def is_execution_blocking_source_code(source_code: str) -> bool:
    return source_code in EXECUTION_BLOCKING_SOURCE_CODES


def derive_blocking_flags(
    *,
    source_system: AuditSourceSystem,
    source_code: str,
    severity: AuditFindingSeverity,
    category: AuditFindingCategory,
    approval_related: bool = False,
) -> tuple[bool, bool]:
    blocking = is_blocking_source_code(source_code)
    execution_blocking = is_execution_blocking_source_code(source_code)

    if category == AuditFindingCategory.CONFLICT:
        blocking = True
        execution_blocking = True

    if severity == AuditFindingSeverity.CRITICAL and category in {
        AuditFindingCategory.SECURITY,
        AuditFindingCategory.TENANT_ISOLATION,
    }:
        blocking = True
        execution_blocking = True

    if approval_related:
        blocking = False
        execution_blocking = True

    if source_code in {
        "approval_required",
        "elevated_approval_required",
        "destructive_approval_required",
    }:
        blocking = False
        execution_blocking = True

    return blocking, execution_blocking


def derive_overall_severity(findings: tuple[AuditFinding, ...]) -> AuditOverallSeverity:
    unresolved = [finding for finding in findings if not finding.resolved]
    if not unresolved:
        return AuditOverallSeverity.NONE

    max_severity = AuditFindingSeverity.INFO
    for finding in unresolved:
        if SEVERITY_ORDER.index(finding.severity) > SEVERITY_ORDER.index(max_severity):
            max_severity = finding.severity

    if max_severity == AuditFindingSeverity.CRITICAL:
        return AuditOverallSeverity.CRITICAL
    if max_severity == AuditFindingSeverity.ERROR:
        return AuditOverallSeverity.ERROR
    if max_severity == AuditFindingSeverity.WARNING:
        return AuditOverallSeverity.WARNING
    return AuditOverallSeverity.INFO
