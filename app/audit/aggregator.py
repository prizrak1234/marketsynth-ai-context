"""Pure audit report aggregation (SKILL-01.6)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.audit.classifications import derive_overall_severity
from app.audit.contracts import (
    ADAPTER_VERSION,
    AuditDecisionReadiness,
    AuditEvidenceReference,
    AuditGenerationMode,
    AuditProvenance,
    AuditReportStatus,
    AuditTargetReference,
    AuditType,
    UnifiedAuditReport,
)
from app.audit.readiness import derive_decision_readiness
from app.audit.serialization import compute_report_hash, deduplicate_findings


def aggregate_audit_reports(
    target: AuditTargetReference,
    source_reports: tuple[UnifiedAuditReport, ...],
    *,
    audit_id: UUID | None = None,
    generated_at: datetime | None = None,
) -> UnifiedAuditReport:
    if not source_reports:
        raise ValueError("At least one source report is required for aggregation.")

    created = generated_at or datetime.now(tz=UTC)
    all_findings = deduplicate_findings(
        tuple(finding for report in source_reports for finding in report.findings),
        target_id=target.target_id,
    )
    all_source_refs = tuple(ref for report in source_reports for ref in report.source_reports)
    all_evidence = tuple(ref for report in source_reports for ref in report.evidence_references)
    all_blockers = tuple(
        dict.fromkeys(blocker for report in source_reports for blocker in report.blockers)
    )
    all_warnings = tuple(
        dict.fromkeys(warning for report in source_reports for warning in report.warnings)
    )
    all_unresolved = tuple(
        dict.fromkeys(
            question for report in source_reports for question in report.unresolved_questions
        )
    )
    all_recommendations = tuple(rec for report in source_reports for rec in report.recommendations)
    source_systems = tuple(
        dict.fromkeys(
            system for report in source_reports for system in report.provenance.source_systems
        )
    )

    statuses = {report.status for report in source_reports}
    if AuditReportStatus.CONFLICTED in statuses:
        status = AuditReportStatus.CONFLICTED
    elif AuditReportStatus.FAILED in statuses:
        status = AuditReportStatus.FAILED
    elif AuditReportStatus.INCOMPLETE in statuses:
        status = AuditReportStatus.INCOMPLETE
    else:
        status = AuditReportStatus.COMPLETE

    package_valid = _extract_package_valid(source_reports)
    quarantine_outcome = _extract_quarantine_outcome(source_reports)
    registry_outcome = _extract_registry_outcome(source_reports)
    connector_outcome = _extract_connector_outcome(source_reports)

    readiness = derive_decision_readiness(
        audit_type=AuditType.COMPOSITE_FOUNDATION_AUDIT,
        findings=all_findings,
        report_status=status,
        package_valid=package_valid,
        quarantine_outcome=quarantine_outcome,
        registry_outcome=registry_outcome,
        connector_outcome=connector_outcome,
    )

    adapter_versions: dict[str, str] = {"audit_adapter": ADAPTER_VERSION}
    for report in source_reports:
        adapter_versions.update(report.adapter_versions)

    audit_report = UnifiedAuditReport(
        audit_id=audit_id or uuid4(),
        audit_type=AuditType.COMPOSITE_FOUNDATION_AUDIT,
        target=target,
        status=status,
        overall_severity=derive_overall_severity(all_findings),
        decision_readiness=readiness,
        findings=all_findings,
        source_reports=all_source_refs,
        evidence_references=_dedupe_evidence(all_evidence),
        blockers=all_blockers,
        warnings=all_warnings,
        unresolved_questions=all_unresolved,
        recommendations=all_recommendations,
        provenance=AuditProvenance(
            generated_by="audit_aggregator",
            generation_mode=AuditGenerationMode.COMPOSITE,
            source_systems=source_systems,
            target_source=target.target_id,
            tenant_context=target.tenant_id,
            project_context=target.project_id,
            human_review_required=any(
                report.provenance.human_review_required for report in source_reports
            ),
            owner_decision_required=any(
                report.provenance.owner_decision_required for report in source_reports
            ),
        ),
        generated_at=created,
        adapter_versions=adapter_versions,
    )
    return audit_report.model_copy(update={"report_hash": compute_report_hash(audit_report)})


def _dedupe_evidence(
    references: tuple[AuditEvidenceReference, ...],
) -> tuple[AuditEvidenceReference, ...]:
    seen: set[str] = set()
    unique: list[AuditEvidenceReference] = []
    for reference in references:
        if reference.evidence_id in seen:
            continue
        seen.add(reference.evidence_id)
        unique.append(reference)
    return tuple(unique)


def _extract_package_valid(reports: tuple[UnifiedAuditReport, ...]) -> bool | None:
    for report in reports:
        if report.audit_type == AuditType.PACKAGE_VALIDATION:
            return report.status != AuditReportStatus.FAILED
    return None


def _extract_quarantine_outcome(reports: tuple[UnifiedAuditReport, ...]):
    from app.skills.quarantine_contracts import QuarantineImportOutcome

    for report in reports:
        if report.audit_type == AuditType.QUARANTINE_IMPORT:
            if report.status == AuditReportStatus.CONFLICTED:
                return QuarantineImportOutcome.CONFLICT
            if report.status == AuditReportStatus.FAILED:
                return QuarantineImportOutcome.REJECTED
            if report.status == AuditReportStatus.INCOMPLETE:
                return QuarantineImportOutcome.INCOMPLETE
            return QuarantineImportOutcome.QUARANTINED
    return None


def _extract_registry_outcome(reports: tuple[UnifiedAuditReport, ...]):
    from app.skills.registry_contracts import SkillProjectionOutcome

    for report in reports:
        if report.audit_type == AuditType.REGISTRY_CONSISTENCY:
            if report.status == AuditReportStatus.CONFLICTED:
                return SkillProjectionOutcome.CONFLICT
            if report.status == AuditReportStatus.FAILED:
                return SkillProjectionOutcome.REJECTED
            return SkillProjectionOutcome.INCOMPLETE
    return None


def _extract_connector_outcome(reports: tuple[UnifiedAuditReport, ...]):
    from app.connectors.contracts import ConnectorPolicyOutcome

    for report in reports:
        if report.audit_type == AuditType.CONNECTOR_POLICY:
            if report.decision_readiness == AuditDecisionReadiness.BLOCKED:
                return ConnectorPolicyOutcome.DENY
            if report.decision_readiness == AuditDecisionReadiness.READY_FOR_APPROVAL_REVIEW:
                return ConnectorPolicyOutcome.REQUIRE_APPROVAL
            if report.decision_readiness == AuditDecisionReadiness.INSUFFICIENT_INFORMATION:
                return ConnectorPolicyOutcome.DEFER
            for finding in report.findings:
                if finding.source_code == "allowed":
                    return ConnectorPolicyOutcome.ALLOW
    return None
