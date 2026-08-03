"""Synthetic audit fixtures for tests (SKILL-01.6)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.audit.adapters import (
    adapt_connector_evidence_descriptor,
    adapt_connector_policy_decision,
    adapt_package_validation_report,
    adapt_quarantine_import_result,
    adapt_registry_conflict,
)
from app.audit.contracts import AuditTargetReference, AuditTargetType
from app.connectors.contracts import (
    ConnectorActionType,
    ConnectorEvidenceDescriptor,
    ConnectorExecutionResultStatus,
    ConnectorPolicyDecision,
    ConnectorPolicyFinding,
    ConnectorPolicyOutcome,
    ConnectorSideEffectClass,
)
from app.schemas.contracts import SkillLifecycleStatus
from app.skills.quarantine_contracts import (
    QuarantineImportOutcome,
    QuarantineImportResult,
    QuarantineProvenanceRecord,
    QuarantineSourceType,
    QuarantineStaticFinding,
    QuarantineStaticFindingSeverity,
)
from app.skills.registry_contracts import SkillRegistryConflict
from app.skills.validation_contracts import (
    SkillPackageValidationReport,
    SkillValidationIssue,
    SkillValidationMode,
    SkillValidationSeverity,
)

FIXED_TIME = datetime(2026, 7, 23, 15, 0, 0, tzinfo=UTC)
TENANT_A = "11111111-1111-1111-1111-111111111111"


def valid_package_validation_report() -> SkillPackageValidationReport:
    report = SkillPackageValidationReport(
        package_path="packages/skills/ms.skill.market_validation",
        skill_id="ms.skill.market_validation",
        skill_version="0.1.0",
        status=SkillLifecycleStatus.CANDIDATE,
        valid=True,
        validation_mode=SkillValidationMode.CANDIDATE,
        package_hash="6c53b5b972e5de900a135b891d8fbbd1641cdb5bf04bb171f83d5023344b8133",
        created_at=FIXED_TIME,
    )
    return report.finalize()


def invalid_manifest_report() -> SkillPackageValidationReport:
    report = SkillPackageValidationReport(
        package_path="fixture/invalid",
        skill_id="ms.skill.invalid",
        skill_version="0.1.0",
        valid=False,
        validation_mode=SkillValidationMode.CANDIDATE,
        created_at=FIXED_TIME,
    )
    report.add_error(
        code="manifest_invalid", message="Manifest YAML is invalid.", location="manifest.yaml"
    )
    return report.finalize()


def secret_finding_report() -> SkillPackageValidationReport:
    report = SkillPackageValidationReport(
        package_path="fixture/secret",
        skill_id="ms.skill.secret",
        skill_version="0.1.0",
        valid=False,
        validation_mode=SkillValidationMode.CANDIDATE,
        created_at=FIXED_TIME,
    )
    report.add_error(
        code="security_secret_detected",
        message="Secret-like content detected in manifest.yaml",
        location="manifest.yaml",
    )
    return report.finalize()


def quarantine_success_result() -> QuarantineImportResult:
    validation = valid_package_validation_report()
    provenance = QuarantineProvenanceRecord(
        import_id="import-success-001",
        source_type=QuarantineSourceType.EXTERNAL_CANDIDATE_FIXTURE,
        source_reference="fixture/external",
        original_path_hash="abc123",
        source_fingerprint="def456",
        materialized_package_hash=validation.package_hash,
        requested_by="test-operator",
        imported_at=FIXED_TIME,
        unresolved_claims=("license_verification",),
    )
    return QuarantineImportResult(
        import_id="import-success-001",
        outcome=QuarantineImportOutcome.QUARANTINED,
        effective_status=SkillLifecycleStatus.QUARANTINED,
        materialized_package_hash=validation.package_hash,
        package_validation_report=validation,
        provenance=provenance,
        audit_required=True,
        approval_required=True,
        production_eligible=False,
        tenant_visible=False,
        created_at=FIXED_TIME,
    )


def quarantine_rejected_result() -> QuarantineImportResult:
    return QuarantineImportResult(
        import_id="import-rejected-001",
        outcome=QuarantineImportOutcome.REJECTED,
        static_findings=(
            QuarantineStaticFinding(
                code="path_traversal",
                severity=QuarantineStaticFindingSeverity.ERROR,
                message="Path traversal attempt detected.",
                location="../secret.txt",
            ),
        ),
        errors=(
            SkillValidationIssue(
                code="security_path_traversal",
                severity=SkillValidationSeverity.ERROR,
                message="Path traversal rejected.",
            ),
        ),
        audit_required=True,
        approval_required=True,
        production_eligible=False,
        tenant_visible=False,
        created_at=FIXED_TIME,
    )


def registry_hash_conflict() -> SkillRegistryConflict:
    return SkillRegistryConflict(
        conflict_code="hash_conflict",
        severity="error",
        involved_records=("ms.skill.external_market_check:0.1.0",),
        explanation="Same skill_id and version with different package hash.",
        remediation_hint="Resolve identity conflict before projection.",
    )


def connector_allow_decision() -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.ALLOW,
        findings=(
            ConnectorPolicyFinding(
                check_id="policy_complete", passed=True, message="All checks passed."
            ),
        ),
        effective_tool_allowed=True,
        reason="allowed",
    )


def connector_deny_decision(*, reason: str = "skill_tool_not_allowed") -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.DENY,
        findings=(
            ConnectorPolicyFinding(
                check_id="skill_tool_intersection", passed=False, message="Denied."
            ),
        ),
        reason=reason,
    )


def connector_require_approval_decision() -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.REQUIRE_APPROVAL,
        findings=(
            ConnectorPolicyFinding(
                check_id="approval_required", passed=False, message="Approval required."
            ),
        ),
        approval_required=True,
        reason="approval_required",
    )


def connector_defer_decision() -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.DEFER,
        findings=(
            ConnectorPolicyFinding(check_id="connector_health", passed=False, message="Degraded."),
        ),
        reason="connector_degraded",
    )


def connector_cross_tenant_deny() -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.DENY,
        findings=(
            ConnectorPolicyFinding(
                check_id="tenant_visibility", passed=False, message="Invisible."
            ),
        ),
        reason="tenant_invisible",
    )


def connector_billing_missing_decision() -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.REQUIRE_APPROVAL,
        findings=(
            ConnectorPolicyFinding(
                check_id="budget_context", passed=False, message="Budget missing."
            ),
        ),
        approval_required=True,
        reason="billing_budget_context_required",
    )


def connector_secret_payload_deny() -> ConnectorPolicyDecision:
    return ConnectorPolicyDecision(
        outcome=ConnectorPolicyOutcome.DENY,
        findings=(
            ConnectorPolicyFinding(
                check_id="input_payload_secrets", passed=False, message="Secret key."
            ),
        ),
        reason="input_payload_secret",
    )


def connector_evidence_descriptor() -> ConnectorEvidenceDescriptor:
    return ConnectorEvidenceDescriptor(
        evidence_id=uuid4(),
        request_id=uuid4(),
        connector_id="fixture.connector.research_read",
        connector_version="0.1.0-fixture",
        tool_id="research.read",
        tenant_id=UUID(TENANT_A),
        project_id=uuid4(),
        action_type=ConnectorActionType.READ,
        side_effect_class=ConnectorSideEffectClass.NONE,
        input_hash="input-hash",
        output_hash="output-hash",
        provider_metadata_hash="metadata-hash",
        started_at=FIXED_TIME,
        finished_at=FIXED_TIME,
        result_status=ConnectorExecutionResultStatus.SUCCEEDED,
    )


def connector_policy_target() -> AuditTargetReference:
    return AuditTargetReference(
        target_type=AuditTargetType.CONNECTOR_POLICY_DECISION,
        connector_id="fixture.connector.research_read",
        tool_id="research.read",
        target_version="0.1.0-fixture",
    )


def adapted_valid_package_report():
    return adapt_package_validation_report(
        valid_package_validation_report(), generated_at=FIXED_TIME
    )


def adapted_quarantine_success():
    return adapt_quarantine_import_result(quarantine_success_result(), generated_at=FIXED_TIME)


def adapted_registry_conflict():
    return adapt_registry_conflict(registry_hash_conflict(), generated_at=FIXED_TIME)


def adapted_connector_allow():
    return adapt_connector_policy_decision(
        connector_allow_decision(),
        target=connector_policy_target(),
        generated_at=FIXED_TIME,
    )


def adapted_connector_evidence():
    return adapt_connector_evidence_descriptor(
        connector_evidence_descriptor(),
        generated_at=FIXED_TIME,
    )
