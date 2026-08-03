"""Decision readiness derivation (SKILL-01.6)."""

from __future__ import annotations

from app.audit.classifications import derive_overall_severity
from app.audit.contracts import (
    AuditDecisionReadiness,
    AuditFinding,
    AuditOverallSeverity,
    AuditReportStatus,
    AuditType,
)
from app.connectors.contracts import ConnectorPolicyOutcome
from app.skills.quarantine_contracts import QuarantineImportOutcome
from app.skills.registry_contracts import SkillProjectionOutcome


def derive_decision_readiness(
    *,
    audit_type: AuditType,
    findings: tuple[AuditFinding, ...],
    report_status: AuditReportStatus,
    package_valid: bool | None = None,
    quarantine_outcome: QuarantineImportOutcome | None = None,
    provenance_present: bool = False,
    registry_outcome: SkillProjectionOutcome | None = None,
    connector_outcome: ConnectorPolicyOutcome | None = None,
) -> AuditDecisionReadiness:
    blocking_findings = [
        finding for finding in findings if finding.blocking and not finding.resolved
    ]
    if blocking_findings or report_status in {
        AuditReportStatus.FAILED,
        AuditReportStatus.CONFLICTED,
    }:
        return AuditDecisionReadiness.BLOCKED

    overall = derive_overall_severity(findings)
    if overall == AuditOverallSeverity.CRITICAL:
        return AuditDecisionReadiness.BLOCKED

    if audit_type == AuditType.CONNECTOR_POLICY and connector_outcome is not None:
        return _connector_policy_readiness(connector_outcome)

    if audit_type == AuditType.QUARANTINE_IMPORT and quarantine_outcome is not None:
        return _quarantine_readiness(quarantine_outcome, provenance_present, findings)

    if audit_type == AuditType.REGISTRY_CONSISTENCY and registry_outcome is not None:
        return _registry_readiness(registry_outcome)

    if audit_type == AuditType.PACKAGE_VALIDATION:
        return _package_validation_readiness(package_valid, findings)

    if audit_type == AuditType.COMPOSITE_FOUNDATION_AUDIT:
        return _composite_readiness(
            findings, package_valid, quarantine_outcome, registry_outcome, connector_outcome
        )

    if report_status == AuditReportStatus.INCOMPLETE:
        return AuditDecisionReadiness.INSUFFICIENT_INFORMATION

    return AuditDecisionReadiness.NOT_READY


def _package_validation_readiness(
    package_valid: bool | None,
    findings: tuple[AuditFinding, ...],
) -> AuditDecisionReadiness:
    if package_valid is False:
        return AuditDecisionReadiness.BLOCKED
    if package_valid is True and not any(f.blocking and not f.resolved for f in findings):
        return AuditDecisionReadiness.READY_FOR_AUDIT
    if any(f.severity.value in {"warning", "info"} and not f.blocking for f in findings):
        return AuditDecisionReadiness.READY_FOR_AUDIT
    return AuditDecisionReadiness.NOT_READY


def _quarantine_readiness(
    outcome: QuarantineImportOutcome,
    provenance_present: bool,
    findings: tuple[AuditFinding, ...],
) -> AuditDecisionReadiness:
    if outcome == QuarantineImportOutcome.REJECTED:
        return AuditDecisionReadiness.BLOCKED
    if outcome == QuarantineImportOutcome.CONFLICT:
        return AuditDecisionReadiness.BLOCKED
    if outcome == QuarantineImportOutcome.INCOMPLETE:
        return AuditDecisionReadiness.INSUFFICIENT_INFORMATION
    if (
        outcome == QuarantineImportOutcome.QUARANTINED
        and provenance_present
        and not any(f.blocking and not f.resolved for f in findings)
    ):
        return AuditDecisionReadiness.READY_FOR_HUMAN_REVIEW
    return AuditDecisionReadiness.NOT_READY


def _registry_readiness(outcome: SkillProjectionOutcome) -> AuditDecisionReadiness:
    if outcome == SkillProjectionOutcome.CONFLICT:
        return AuditDecisionReadiness.BLOCKED
    if outcome in {SkillProjectionOutcome.REJECTED, SkillProjectionOutcome.INCOMPLETE}:
        return AuditDecisionReadiness.NOT_READY
    return AuditDecisionReadiness.NOT_READY


def _connector_policy_readiness(outcome: ConnectorPolicyOutcome) -> AuditDecisionReadiness:
    if outcome == ConnectorPolicyOutcome.DENY:
        return AuditDecisionReadiness.BLOCKED
    if outcome == ConnectorPolicyOutcome.REQUIRE_APPROVAL:
        return AuditDecisionReadiness.READY_FOR_APPROVAL_REVIEW
    if outcome == ConnectorPolicyOutcome.DEFER:
        return AuditDecisionReadiness.INSUFFICIENT_INFORMATION
    if outcome == ConnectorPolicyOutcome.UNAVAILABLE:
        return AuditDecisionReadiness.INSUFFICIENT_INFORMATION
    if outcome == ConnectorPolicyOutcome.ALLOW:
        return AuditDecisionReadiness.NOT_READY
    if outcome == ConnectorPolicyOutcome.REQUIRE_ADDITIONAL_CONTEXT:
        return AuditDecisionReadiness.INSUFFICIENT_INFORMATION
    return AuditDecisionReadiness.NOT_READY


def _composite_readiness(
    findings: tuple[AuditFinding, ...],
    package_valid: bool | None,
    quarantine_outcome: QuarantineImportOutcome | None,
    registry_outcome: SkillProjectionOutcome | None,
    connector_outcome: ConnectorPolicyOutcome | None,
) -> AuditDecisionReadiness:
    if any(f.blocking and not f.resolved for f in findings):
        return AuditDecisionReadiness.BLOCKED
    if registry_outcome == SkillProjectionOutcome.CONFLICT:
        return AuditDecisionReadiness.BLOCKED
    if connector_outcome == ConnectorPolicyOutcome.DENY:
        return AuditDecisionReadiness.BLOCKED
    if package_valid is True:
        return AuditDecisionReadiness.READY_FOR_AUDIT
    if quarantine_outcome == QuarantineImportOutcome.QUARANTINED:
        return AuditDecisionReadiness.READY_FOR_HUMAN_REVIEW
    if connector_outcome == ConnectorPolicyOutcome.REQUIRE_APPROVAL:
        return AuditDecisionReadiness.READY_FOR_APPROVAL_REVIEW
    return AuditDecisionReadiness.NOT_READY
