"""SKILL-01.6 — Unified audit report schema tests."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.audit import (
    AuditDecisionReadiness,
    AuditFindingSeverity,
    AuditOverallSeverity,
    AuditReportStatus,
    AuditType,
    UnifiedAuditReport,
    adapt_connector_evidence_descriptor,
    adapt_connector_policy_decision,
    adapt_package_validation_report,
    adapt_quarantine_import_result,
    adapt_registry_conflict,
    aggregate_audit_reports,
    deduplicate_findings,
    serialize_report,
    validate_audit_type,
    validate_finding_category,
)
from app.audit.contracts import AuditTargetReference, AuditTargetType
from app.audit.fixtures import (
    FIXED_TIME,
    adapted_connector_allow,
    adapted_quarantine_success,
    adapted_registry_conflict,
    adapted_valid_package_report,
    connector_allow_decision,
    connector_billing_missing_decision,
    connector_cross_tenant_deny,
    connector_defer_decision,
    connector_deny_decision,
    connector_evidence_descriptor,
    connector_policy_target,
    connector_require_approval_decision,
    connector_secret_payload_deny,
    invalid_manifest_report,
    quarantine_rejected_result,
    quarantine_success_result,
    registry_hash_conflict,
    secret_finding_report,
    valid_package_validation_report,
)
from app.audit.redaction import redact_payload, sanitize_location
from app.connectors.contracts import ConnectorPolicyOutcome
from app.skills.package_validator import validate_skill_package
from app.skills.quarantine_contracts import QuarantineImportOutcome
from app.skills.validation_contracts import (
    SkillPackageValidationReport,
    SkillSchemaValidationResult,
    SkillValidationIssue,
    SkillValidationMode,
    SkillValidationSeverity,
)
from pydantic import ValidationError

FROZEN_PACKAGE = (
    Path(__file__).resolve().parents[1] / "packages" / "skills" / "ms.skill.market_validation"
)


def test_audit_contracts_are_immutable() -> None:
    report = adapted_valid_package_report()
    with pytest.raises(ValidationError):
        report.status = AuditReportStatus.FAILED  # type: ignore[misc]


def test_unknown_audit_type_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown audit type"):
        validate_audit_type("approved")


def test_unknown_finding_category_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown finding category"):
        validate_finding_category("auto_approve")


def test_package_validation_report_adapts_correctly() -> None:
    report = adapt_package_validation_report(
        valid_package_validation_report(), generated_at=FIXED_TIME
    )
    assert report.audit_type == AuditType.PACKAGE_VALIDATION
    assert report.target.target_id == "ms.skill.market_validation"
    assert report.source_reports[0].source_system.value == "skill_package_validator"
    assert all(finding.source_code for finding in report.findings)


def test_quarantine_result_adapts_correctly() -> None:
    report = adapt_quarantine_import_result(quarantine_success_result(), generated_at=FIXED_TIME)
    assert report.audit_type == AuditType.QUARANTINE_IMPORT
    assert report.target.import_id == "import-success-001"
    assert report.unresolved_questions == ("license_verification",)


def test_registry_conflict_adapts_correctly() -> None:
    report = adapt_registry_conflict(registry_hash_conflict(), generated_at=FIXED_TIME)
    assert report.findings[0].source_code == "hash_conflict"
    assert report.findings[0].category.value == "conflict"


def test_connector_policy_decision_adapts_correctly() -> None:
    report = adapt_connector_policy_decision(
        connector_deny_decision(),
        target=connector_policy_target(),
        generated_at=FIXED_TIME,
    )
    assert report.findings[0].source_code == "skill_tool_not_allowed"
    assert report.decision_readiness == AuditDecisionReadiness.BLOCKED


def test_connector_evidence_descriptor_adapts_correctly() -> None:
    report = adapt_connector_evidence_descriptor(
        connector_evidence_descriptor(), generated_at=FIXED_TIME
    )
    assert len(report.evidence_references) == 1
    assert report.evidence_references[0].input_hash == "input-hash"


def test_severity_mapping_deterministic() -> None:
    first = adapt_package_validation_report(secret_finding_report(), generated_at=FIXED_TIME)
    second = adapt_package_validation_report(secret_finding_report(), generated_at=FIXED_TIME)
    assert (
        first.findings[0].severity == second.findings[0].severity == AuditFindingSeverity.CRITICAL
    )


def test_approval_required_not_security_error() -> None:
    report = adapt_connector_policy_decision(
        connector_require_approval_decision(),
        target=connector_policy_target(),
        generated_at=FIXED_TIME,
    )
    assert report.findings[0].severity in {AuditFindingSeverity.INFO, AuditFindingSeverity.WARNING}
    assert report.findings[0].severity != AuditFindingSeverity.CRITICAL
    assert report.findings[0].blocking is False


def test_cross_tenant_finding_is_critical() -> None:
    report = adapt_connector_policy_decision(
        connector_cross_tenant_deny(),
        target=connector_policy_target(),
        generated_at=FIXED_TIME,
    )
    assert report.findings[0].severity == AuditFindingSeverity.CRITICAL


def test_secret_like_payload_finding_is_critical() -> None:
    report = adapt_connector_policy_decision(
        connector_secret_payload_deny(),
        target=connector_policy_target(),
        generated_at=FIXED_TIME,
    )
    assert report.findings[0].severity == AuditFindingSeverity.CRITICAL


def test_path_traversal_is_blocking() -> None:
    report = adapt_quarantine_import_result(quarantine_rejected_result(), generated_at=FIXED_TIME)
    traversal = next(f for f in report.findings if f.source_code == "path_traversal")
    assert traversal.blocking is True


def test_invalid_schema_is_blocking() -> None:
    validation = SkillPackageValidationReport(
        package_path="fixture/schema",
        skill_id="ms.skill.schema",
        skill_version="0.1.0",
        valid=False,
        validation_mode=SkillValidationMode.CANDIDATE,
        created_at=FIXED_TIME,
        schema_results=[
            SkillSchemaValidationResult(
                schema_ref="schemas/input.schema.json",
                valid=False,
                errors=["missing field"],
            ),
        ],
    )
    report = adapt_package_validation_report(validation.finalize(), generated_at=FIXED_TIME)
    schema_finding = next(f for f in report.findings if f.source_code == "schema_invalid")
    assert schema_finding.blocking is True


def test_id_version_hash_conflict_is_blocking() -> None:
    report = adapted_registry_conflict()
    assert report.findings[0].blocking is True


def test_valid_candidate_package_becomes_ready_for_audit() -> None:
    report = adapted_valid_package_report()
    assert report.decision_readiness == AuditDecisionReadiness.READY_FOR_AUDIT


def test_candidate_never_becomes_activation_ready() -> None:
    report = adapted_valid_package_report()
    readiness_values = {item.value for item in AuditDecisionReadiness}
    assert "ready_for_activation" not in readiness_values
    assert report.status.value not in {"approved", "rejected", "active"}


def test_quarantine_success_becomes_ready_for_human_review() -> None:
    report = adapted_quarantine_success()
    assert report.decision_readiness == AuditDecisionReadiness.READY_FOR_HUMAN_REVIEW


def test_quarantine_remains_quarantined() -> None:
    result = quarantine_success_result()
    assert result.outcome == QuarantineImportOutcome.QUARANTINED
    assert result.effective_status.value == "quarantined"
    assert result.production_eligible is False


def test_connector_allow_maps_correctly() -> None:
    report = adapted_connector_allow()
    assert report.decision_readiness == AuditDecisionReadiness.NOT_READY
    assert report.findings[0].source_code == "allowed"
    assert report.overall_severity == AuditOverallSeverity.INFO


def test_connector_require_approval_maps_to_ready_for_approval_review() -> None:
    report = adapt_connector_policy_decision(
        connector_require_approval_decision(),
        target=connector_policy_target(),
        generated_at=FIXED_TIME,
    )
    assert report.decision_readiness == AuditDecisionReadiness.READY_FOR_APPROVAL_REVIEW


def test_connector_deny_maps_to_blocked() -> None:
    report = adapt_connector_policy_decision(
        connector_deny_decision(),
        target=connector_policy_target(),
        generated_at=FIXED_TIME,
    )
    assert report.decision_readiness == AuditDecisionReadiness.BLOCKED


def test_connector_defer_maps_to_insufficient_information() -> None:
    report = adapt_connector_policy_decision(
        connector_defer_decision(),
        target=connector_policy_target(),
        generated_at=FIXED_TIME,
    )
    assert report.decision_readiness == AuditDecisionReadiness.INSUFFICIENT_INFORMATION


def test_mixed_findings_derive_highest_severity() -> None:
    package = adapt_package_validation_report(
        valid_package_validation_report(), generated_at=FIXED_TIME
    )
    package = package.model_copy(
        update={
            "findings": (
                *package.findings,
                *adapt_package_validation_report(
                    secret_finding_report(), generated_at=FIXED_TIME
                ).findings,
            )
        }
    )
    target = AuditTargetReference(target_type=AuditTargetType.SKILL_PACKAGE, target_id="mixed")
    composite = aggregate_audit_reports(
        target, (package, adapted_registry_conflict()), generated_at=FIXED_TIME
    )
    assert composite.overall_severity == AuditOverallSeverity.CRITICAL


def test_successful_checks_do_not_downgrade_errors() -> None:
    report = adapt_package_validation_report(secret_finding_report(), generated_at=FIXED_TIME)
    assert report.overall_severity == AuditOverallSeverity.CRITICAL


def test_finding_order_deterministic() -> None:
    target = AuditTargetReference(target_type=AuditTargetType.SKILL_PACKAGE, target_id="order")
    first = aggregate_audit_reports(
        target,
        (adapted_valid_package_report(), adapted_registry_conflict()),
        generated_at=FIXED_TIME,
    )
    second = aggregate_audit_reports(
        target,
        (adapted_valid_package_report(), adapted_registry_conflict()),
        generated_at=FIXED_TIME,
    )
    assert [finding.finding_id for finding in first.findings] == [
        finding.finding_id for finding in second.findings
    ]


def test_finding_deduplication_deterministic() -> None:
    report = adapted_valid_package_report()
    duplicated = aggregate_audit_reports(
        report.target,
        (report, report),
        generated_at=FIXED_TIME,
    )
    assert len(duplicated.findings) == len(report.findings)


def test_different_source_codes_are_not_merged() -> None:
    package = adapt_package_validation_report(invalid_manifest_report(), generated_at=FIXED_TIME)
    secret = adapt_package_validation_report(secret_finding_report(), generated_at=FIXED_TIME)
    target = AuditTargetReference(target_type=AuditTargetType.SKILL_PACKAGE, target_id="distinct")
    composite = aggregate_audit_reports(target, (package, secret), generated_at=FIXED_TIME)
    codes = {finding.source_code for finding in composite.findings}
    assert "manifest_invalid" in codes
    assert "security_secret_detected" in codes


def test_source_report_references_preserved() -> None:
    target = AuditTargetReference(target_type=AuditTargetType.SKILL_PACKAGE, target_id="refs")
    composite = aggregate_audit_reports(
        target,
        (adapted_valid_package_report(), adapted_quarantine_success()),
        generated_at=FIXED_TIME,
    )
    systems = {ref.source_system.value for ref in composite.source_reports}
    assert "skill_package_validator" in systems
    assert "quarantine_import_adapter" in systems


def test_source_objects_are_not_mutated() -> None:
    validation = valid_package_validation_report()
    snapshot = copy.deepcopy(validation.model_dump())
    adapt_package_validation_report(validation, generated_at=FIXED_TIME)
    assert validation.model_dump() == snapshot


def test_report_hash_deterministic() -> None:
    first = adapted_valid_package_report()
    second = adapt_package_validation_report(
        valid_package_validation_report(), generated_at=FIXED_TIME
    )
    assert first.report_hash == second.report_hash


def test_audit_id_does_not_affect_semantic_hash() -> None:
    first = adapt_package_validation_report(
        valid_package_validation_report(),
        audit_id=uuid4(),
        generated_at=FIXED_TIME,
    )
    second = adapt_package_validation_report(
        valid_package_validation_report(),
        audit_id=uuid4(),
        generated_at=FIXED_TIME,
    )
    assert first.report_hash == second.report_hash


def test_generated_timestamp_does_not_affect_semantic_hash() -> None:
    first = adapt_package_validation_report(
        valid_package_validation_report(), generated_at=FIXED_TIME
    )
    second = adapt_package_validation_report(
        valid_package_validation_report(),
        generated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert first.report_hash == second.report_hash


def test_redaction_removes_secret_values() -> None:
    redacted = redact_payload({"api_key": "super-secret", "safe": "ok"})
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["safe"] == "ok"


def test_finding_remains_after_value_redaction() -> None:
    report = adapt_package_validation_report(secret_finding_report(), generated_at=FIXED_TIME)
    assert any(finding.source_code == "security_secret_detected" for finding in report.findings)


def test_absolute_paths_not_present() -> None:
    issue = SkillValidationIssue(
        code="structure_invalid",
        severity=SkillValidationSeverity.ERROR,
        message=r"Bad file at C:\Users\secret\manifest.yaml",
        location=r"C:\Users\secret\manifest.yaml",
    )
    report = SkillPackageValidationReport(
        package_path="fixture",
        valid=False,
        validation_mode=SkillValidationMode.CANDIDATE,
        errors=[issue],
        created_at=FIXED_TIME,
    )
    adapted = adapt_package_validation_report(report.finalize(), generated_at=FIXED_TIME)
    serialized = serialize_report(adapted)
    assert "C:\\Users" not in serialized


def test_cross_tenant_hidden_ids_not_exposed() -> None:
    report = adapt_connector_policy_decision(
        connector_cross_tenant_deny(),
        target=connector_policy_target(),
        generated_at=FIXED_TIME,
    )
    serialized = serialize_report(report)
    assert "tenant_invisible" in serialized


def test_existing_evidence_ids_can_be_referenced() -> None:
    evidence_id = str(uuid4())
    descriptor = connector_evidence_descriptor().model_copy(
        update={"evidence_id": UUID(evidence_id)}
    )
    report = adapt_connector_evidence_descriptor(descriptor, generated_at=FIXED_TIME)
    assert report.evidence_references[0].evidence_id == evidence_id


def test_no_evidence_persistence_created() -> None:
    import app.audit

    source = Path(app.audit.__file__).read_text(encoding="utf-8")
    assert "repository" not in source.lower()
    assert "session" not in source.lower()


def test_recommendations_do_not_mutate_state() -> None:
    report = adapted_registry_conflict()
    assert report.recommendations
    assert not hasattr(report, "approve")
    assert not hasattr(report, "activate")


def test_no_approve_activate_fields_or_methods_exist() -> None:
    fields = UnifiedAuditReport.model_fields
    assert "approved" not in fields
    assert "activated" not in fields
    assert "rejected" not in fields


def test_composite_report_contains_package_registry_and_connector_sources() -> None:
    target = AuditTargetReference(
        target_type=AuditTargetType.SKILL_PACKAGE,
        target_id="ms.skill.market_validation",
        target_version="0.1.0",
    )
    composite = aggregate_audit_reports(
        target,
        (
            adapted_valid_package_report(),
            adapted_registry_conflict(),
            adapted_connector_allow(),
        ),
        generated_at=FIXED_TIME,
    )
    assert composite.audit_type == AuditType.COMPOSITE_FOUNDATION_AUDIT
    systems = {ref.source_system.value for ref in composite.source_reports}
    assert "skill_package_validator" in systems
    assert "skill_registry_conflict_detector" in systems
    assert "connector_policy_engine" in systems


def test_report_serialization_stable() -> None:
    report = adapted_valid_package_report()
    assert serialize_report(report) == serialize_report(report)


def test_frozen_package_validation_adapted_with_real_validator() -> None:
    validation = validate_skill_package(FROZEN_PACKAGE)
    report = adapt_package_validation_report(validation, generated_at=FIXED_TIME)
    assert report.target.target_id == "ms.skill.market_validation"
    assert report.decision_readiness == AuditDecisionReadiness.READY_FOR_AUDIT


def test_connector_billing_missing_maps_correctly() -> None:
    report = adapt_connector_policy_decision(
        connector_billing_missing_decision(),
        target=connector_policy_target(),
        generated_at=FIXED_TIME,
    )
    assert report.decision_readiness == AuditDecisionReadiness.READY_FOR_APPROVAL_REVIEW
    assert any("billing" in finding.source_code for finding in report.findings)


def test_deduplicate_preserves_different_codes() -> None:
    findings = adapted_valid_package_report().findings + adapted_registry_conflict().findings
    deduped = deduplicate_findings(findings, target_id="x")
    assert len(deduped) == len(findings)


def test_redact_text_sanitizes_location() -> None:
    assert sanitize_location(r"C:\secret\path\manifest.yaml") == "[PATH]"


def test_connector_policy_allow_outcome_preserved() -> None:
    decision = connector_allow_decision()
    assert decision.outcome == ConnectorPolicyOutcome.ALLOW
