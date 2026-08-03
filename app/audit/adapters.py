"""Pure source-report adapters for unified audit layer (SKILL-01.6)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.audit.classifications import (
    derive_blocking_flags,
    map_connector_policy_outcome,
    map_package_validator_code_category,
    map_package_validator_severity,
    map_quarantine_static_code_severity,
    map_registry_conflict_severity,
)
from app.audit.contracts import (
    ADAPTER_VERSION,
    AuditDecisionReadiness,
    AuditEvidenceReference,
    AuditFinding,
    AuditFindingCategory,
    AuditFindingSeverity,
    AuditGenerationMode,
    AuditOverallSeverity,
    AuditProvenance,
    AuditRecommendation,
    AuditRecommendationType,
    AuditReportStatus,
    AuditSourceReference,
    AuditSourceSystem,
    AuditTargetReference,
    AuditTargetType,
    AuditType,
    UnifiedAuditReport,
)
from app.audit.readiness import derive_decision_readiness
from app.audit.redaction import redact_text, sanitize_location
from app.audit.serialization import canonical_json, compute_report_hash
from app.connectors.contracts import (
    ConnectorEvidenceDescriptor,
    ConnectorExecutionResult,
    ConnectorPolicyDecision,
    ConnectorPolicyOutcome,
)
from app.skills.quarantine_contracts import QuarantineImportResult
from app.skills.registry_contracts import SkillRegistryConflict, SkillRegistryProjectionResult
from app.skills.validation_contracts import (
    VALIDATOR_VERSION,
    SkillPackageValidationReport,
    SkillValidationIssue,
)

AUDIT_ADAPTER_VERSION = ADAPTER_VERSION


def hash_source_payload(payload: Any) -> str:
    data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    encoded = canonical_json(data).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _finding_id(source_system: AuditSourceSystem, source_code: str, index: int) -> str:
    return f"{source_system.value}:{source_code}:{index}"


def _issue_to_finding(
    issue: SkillValidationIssue,
    *,
    index: int,
    source_hash: str,
    created_at: datetime,
) -> AuditFinding:
    severity = map_package_validator_severity(issue.severity)
    if issue.code in {
        "security_secret_detected",
        "security_path_traversal",
        "security_symlink_escape",
    }:
        severity = AuditFindingSeverity.CRITICAL
    category = map_package_validator_code_category(issue.code)
    blocking, execution_blocking = derive_blocking_flags(
        source_system=AuditSourceSystem.SKILL_PACKAGE_VALIDATOR,
        source_code=issue.code,
        severity=severity,
        category=category,
    )
    if issue.code.startswith("security_"):
        blocking = True
        execution_blocking = True
    if issue.code in {"schema_invalid", "manifest_invalid", "identity_conflict", "hash_conflict"}:
        blocking = True
        execution_blocking = True
    return AuditFinding(
        finding_id=_finding_id(AuditSourceSystem.SKILL_PACKAGE_VALIDATOR, issue.code, index),
        source_system=AuditSourceSystem.SKILL_PACKAGE_VALIDATOR,
        source_code=issue.code,
        category=category,
        severity=severity,
        title=issue.code.replace("_", " "),
        message=redact_text(issue.message),
        location=sanitize_location(issue.location),
        rule_reference=issue.rule_reference,
        remediation_hint=issue.remediation_hint,
        blocking=blocking,
        execution_blocking=execution_blocking,
        source_payload_hash=source_hash,
        created_at=created_at,
    )


def adapt_package_validation_report(
    report: SkillPackageValidationReport,
    *,
    audit_id: UUID | None = None,
    generated_at: datetime | None = None,
) -> UnifiedAuditReport:
    created = generated_at or report.created_at
    source_hash = hash_source_payload(report)
    findings: list[AuditFinding] = []
    for index, issue in enumerate([*report.errors, *report.warnings, *report.security_findings]):
        findings.append(
            _issue_to_finding(issue, index=index, source_hash=source_hash, created_at=created)
        )

    for index, schema_result in enumerate(report.schema_results):
        if schema_result.valid:
            continue
        code = "schema_invalid"
        findings.append(
            AuditFinding(
                finding_id=_finding_id(AuditSourceSystem.SKILL_PACKAGE_VALIDATOR, code, index),
                source_system=AuditSourceSystem.SKILL_PACKAGE_VALIDATOR,
                source_code=code,
                category=AuditFindingCategory.SCHEMA,
                severity=AuditFindingSeverity.ERROR,
                title="Schema validation failed",
                message=f"Schema {schema_result.schema_ref} is invalid.",
                location=schema_result.schema_ref,
                blocking=True,
                execution_blocking=True,
                source_payload_hash=source_hash,
                created_at=created,
            )
        )

    target = AuditTargetReference(
        target_type=AuditTargetType.SKILL_PACKAGE,
        target_id=report.skill_id,
        target_version=report.skill_version,
        package_hash=report.package_hash,
        lifecycle_status=report.status.value if report.status else None,
    )
    status = AuditReportStatus.COMPLETE if report.valid else AuditReportStatus.FAILED
    readiness = derive_decision_readiness(
        audit_type=AuditType.PACKAGE_VALIDATION,
        findings=tuple(findings),
        report_status=status,
        package_valid=report.valid,
    )
    provenance = AuditProvenance(
        generated_by="skill_package_validator",
        generation_mode=AuditGenerationMode.AUTOMATED_STATIC,
        source_systems=(AuditSourceSystem.SKILL_PACKAGE_VALIDATOR,),
        human_review_required=False,
        owner_decision_required=False,
    )
    source_ref = AuditSourceReference(
        source_system=AuditSourceSystem.SKILL_PACKAGE_VALIDATOR,
        source_report_id=report.package_hash or report.skill_id or "unknown",
        source_version=report.validator_version,
        source_hash=source_hash,
        generated_at=created,
        adapter_version=AUDIT_ADAPTER_VERSION,
    )
    blockers = tuple(
        finding.source_code for finding in findings if finding.blocking and not finding.resolved
    )
    warnings = tuple(
        finding.message for finding in findings if finding.severity == AuditFindingSeverity.WARNING
    )
    recommendations = _recommendations_from_findings(findings)
    audit_report = UnifiedAuditReport(
        audit_id=audit_id or uuid4(),
        audit_type=AuditType.PACKAGE_VALIDATION,
        target=target,
        status=status,
        overall_severity=_overall_from_findings(findings),
        decision_readiness=readiness,
        findings=tuple(findings),
        source_reports=(source_ref,),
        blockers=blockers,
        warnings=warnings,
        recommendations=recommendations,
        provenance=provenance,
        generated_at=created,
        adapter_versions={
            "skill_package_validator": report.validator_version,
            "audit_adapter": AUDIT_ADAPTER_VERSION,
        },
    )
    return audit_report.model_copy(update={"report_hash": compute_report_hash(audit_report)})


def adapt_quarantine_import_result(
    result: QuarantineImportResult,
    *,
    audit_id: UUID | None = None,
    generated_at: datetime | None = None,
) -> UnifiedAuditReport:
    created = generated_at or result.created_at
    source_hash = hash_source_payload(result)
    findings: list[AuditFinding] = []

    for index, finding in enumerate(result.static_findings):
        severity = map_quarantine_static_code_severity(finding.code, finding.severity)
        category = (
            AuditFindingCategory.SECURITY
            if finding.code.startswith(("symlink", "secret", "executable", "path"))
            else AuditFindingCategory.STRUCTURE
        )
        blocking, execution_blocking = derive_blocking_flags(
            source_system=AuditSourceSystem.QUARANTINE_IMPORT_ADAPTER,
            source_code=finding.code,
            severity=severity,
            category=category,
        )
        findings.append(
            AuditFinding(
                finding_id=_finding_id(
                    AuditSourceSystem.QUARANTINE_IMPORT_ADAPTER, finding.code, index
                ),
                source_system=AuditSourceSystem.QUARANTINE_IMPORT_ADAPTER,
                source_code=finding.code,
                category=category,
                severity=severity,
                title=finding.code.replace("_", " "),
                message=redact_text(finding.message),
                location=sanitize_location(finding.location),
                rule_reference=finding.rule_reference,
                blocking=blocking,
                execution_blocking=execution_blocking,
                source_payload_hash=source_hash,
                created_at=created,
            )
        )

    for index, issue in enumerate([*result.errors, *result.warnings]):
        findings.append(
            _issue_to_finding(
                issue,
                index=index + len(result.static_findings),
                source_hash=source_hash,
                created_at=created,
            )
        )

    if result.provenance is None:
        findings.append(
            AuditFinding(
                finding_id=_finding_id(
                    AuditSourceSystem.QUARANTINE_IMPORT_ADAPTER, "provenance_missing", 0
                ),
                source_system=AuditSourceSystem.QUARANTINE_IMPORT_ADAPTER,
                source_code="provenance_missing",
                category=AuditFindingCategory.PROVENANCE,
                severity=AuditFindingSeverity.ERROR,
                title="Provenance missing",
                message="Quarantine import is missing required provenance.",
                blocking=True,
                execution_blocking=True,
                source_payload_hash=source_hash,
                created_at=created,
            )
        )

    if result.provenance and result.provenance.unresolved_claims:
        for index, claim in enumerate(result.provenance.unresolved_claims):
            findings.append(
                AuditFinding(
                    finding_id=_finding_id(
                        AuditSourceSystem.QUARANTINE_IMPORT_ADAPTER, f"unresolved_{claim}", index
                    ),
                    source_system=AuditSourceSystem.QUARANTINE_IMPORT_ADAPTER,
                    source_code=f"unresolved_{claim}",
                    category=AuditFindingCategory.LICENSING,
                    severity=AuditFindingSeverity.WARNING,
                    title=f"Unresolved claim: {claim}",
                    message=f"Claim '{claim}' remains unresolved.",
                    blocking=False,
                    execution_blocking=False,
                    source_payload_hash=source_hash,
                    created_at=created,
                )
            )

    target = AuditTargetReference(
        target_type=AuditTargetType.SKILL_IMPORT,
        target_id=result.provenance.declared_author if result.provenance else None,
        package_hash=result.materialized_package_hash,
        import_id=result.import_id,
        lifecycle_status=result.effective_status.value if result.effective_status else None,
        tenant_id=result.provenance.tenant_id if result.provenance else None,
        project_id=result.provenance.project_id if result.provenance else None,
    )
    status_map = {
        "quarantined": AuditReportStatus.COMPLETE,
        "rejected": AuditReportStatus.FAILED,
        "incomplete": AuditReportStatus.INCOMPLETE,
        "conflict": AuditReportStatus.CONFLICTED,
    }
    status = status_map.get(result.outcome.value, AuditReportStatus.INCOMPLETE)
    readiness = derive_decision_readiness(
        audit_type=AuditType.QUARANTINE_IMPORT,
        findings=tuple(findings),
        report_status=status,
        quarantine_outcome=result.outcome,
        provenance_present=result.provenance is not None,
    )
    provenance = AuditProvenance(
        generated_by="quarantine_import_adapter",
        generation_mode=AuditGenerationMode.AUTOMATED_STATIC,
        source_systems=(AuditSourceSystem.QUARANTINE_IMPORT_ADAPTER,),
        correlation_id=result.provenance.source_reference if result.provenance else None,
        human_review_required=result.audit_required,
        owner_decision_required=result.approval_required,
    )
    source_ref = AuditSourceReference(
        source_system=AuditSourceSystem.QUARANTINE_IMPORT_ADAPTER,
        source_report_id=result.import_id,
        source_version=result.adapter_version,
        source_hash=source_hash,
        generated_at=created,
        adapter_version=AUDIT_ADAPTER_VERSION,
    )
    unresolved = tuple(result.provenance.unresolved_claims if result.provenance else ())
    audit_report = UnifiedAuditReport(
        audit_id=audit_id or uuid4(),
        audit_type=AuditType.QUARANTINE_IMPORT,
        target=target,
        status=status,
        overall_severity=_overall_from_findings(findings),
        decision_readiness=readiness,
        findings=tuple(findings),
        source_reports=(source_ref,),
        blockers=tuple(f.source_code for f in findings if f.blocking and not f.resolved),
        warnings=tuple(f.message for f in findings if f.severity == AuditFindingSeverity.WARNING),
        unresolved_questions=unresolved,
        recommendations=_recommendations_from_findings(findings),
        provenance=provenance,
        generated_at=created,
        adapter_versions={
            "quarantine_import_adapter": result.adapter_version,
            "audit_adapter": AUDIT_ADAPTER_VERSION,
        },
    )
    return audit_report.model_copy(update={"report_hash": compute_report_hash(audit_report)})


def adapt_registry_conflict(
    conflict: SkillRegistryConflict,
    *,
    target: AuditTargetReference | None = None,
    audit_id: UUID | None = None,
    generated_at: datetime | None = None,
) -> UnifiedAuditReport:
    created = generated_at or datetime.now(tz=UTC)
    source_hash = hash_source_payload(conflict)
    severity = map_registry_conflict_severity(conflict.severity)
    blocking = conflict.conflict_code in {
        "identity_conflict",
        "hash_conflict",
        "source_identity_conflict",
        "lifecycle_conflict",
    } or severity in {AuditFindingSeverity.ERROR, AuditFindingSeverity.CRITICAL}
    finding = AuditFinding(
        finding_id=_finding_id(
            AuditSourceSystem.SKILL_REGISTRY_CONFLICT_DETECTOR, conflict.conflict_code, 0
        ),
        source_system=AuditSourceSystem.SKILL_REGISTRY_CONFLICT_DETECTOR,
        source_code=conflict.conflict_code,
        category=AuditFindingCategory.CONFLICT,
        severity=severity,
        title=conflict.conflict_code.replace("_", " "),
        message=redact_text(conflict.explanation),
        remediation_hint=conflict.remediation_hint,
        blocking=blocking,
        execution_blocking=blocking,
        related_target_ids=conflict.involved_records,
        source_payload_hash=source_hash,
        created_at=created,
    )
    audit_target = target or AuditTargetReference(
        target_type=AuditTargetType.SKILL_REGISTRY_RECORD,
        target_id=conflict.involved_records[0] if conflict.involved_records else None,
    )
    audit_report = UnifiedAuditReport(
        audit_id=audit_id or uuid4(),
        audit_type=AuditType.REGISTRY_CONSISTENCY,
        target=audit_target,
        status=AuditReportStatus.CONFLICTED,
        overall_severity=_overall_from_findings((finding,)),
        decision_readiness=AuditDecisionReadiness.BLOCKED,
        findings=(finding,),
        source_reports=(
            AuditSourceReference(
                source_system=AuditSourceSystem.SKILL_REGISTRY_CONFLICT_DETECTOR,
                source_report_id=conflict.conflict_code,
                source_version=VALIDATOR_VERSION,
                source_hash=source_hash,
                generated_at=created,
                adapter_version=AUDIT_ADAPTER_VERSION,
            ),
        ),
        blockers=(conflict.conflict_code,),
        recommendations=(
            AuditRecommendation(
                recommendation_type=AuditRecommendationType.RESOLVE_IDENTITY_CONFLICT,
                message=conflict.explanation,
                related_finding_ids=(finding.finding_id,),
            ),
        ),
        provenance=AuditProvenance(
            generated_by="skill_registry_conflict_detector",
            generation_mode=AuditGenerationMode.AUTOMATED_STATIC,
            source_systems=(AuditSourceSystem.SKILL_REGISTRY_CONFLICT_DETECTOR,),
            human_review_required=True,
            owner_decision_required=True,
        ),
        generated_at=created,
        adapter_versions={"audit_adapter": AUDIT_ADAPTER_VERSION},
    )
    return audit_report.model_copy(update={"report_hash": compute_report_hash(audit_report)})


def adapt_registry_projection_result(
    projection: SkillRegistryProjectionResult,
    *,
    target: AuditTargetReference | None = None,
    audit_id: UUID | None = None,
    generated_at: datetime | None = None,
) -> UnifiedAuditReport:
    created = generated_at or datetime.now(tz=UTC)
    source_hash = hash_source_payload(projection)
    severity = (
        AuditFindingSeverity.ERROR
        if projection.outcome == SkillProjectionOutcome.CONFLICT
        else AuditFindingSeverity.WARNING
    )
    finding = AuditFinding(
        finding_id=_finding_id(
            AuditSourceSystem.SKILL_REGISTRY_PROJECTION, projection.reason_code, 0
        ),
        source_system=AuditSourceSystem.SKILL_REGISTRY_PROJECTION,
        source_code=projection.reason_code,
        category=AuditFindingCategory.LIFECYCLE
        if projection.outcome != SkillProjectionOutcome.CONFLICT
        else AuditFindingCategory.CONFLICT,
        severity=severity,
        title=projection.reason_code.replace("_", " "),
        message=redact_text(projection.explanation or projection.reason_code),
        remediation_hint=projection.remediation_hint,
        blocking=projection.outcome
        in {SkillProjectionOutcome.CONFLICT, SkillProjectionOutcome.REJECTED},
        execution_blocking=projection.outcome
        in {SkillProjectionOutcome.CONFLICT, SkillProjectionOutcome.REJECTED},
        source_payload_hash=source_hash,
        created_at=created,
    )
    version = projection.version_record
    audit_target = target or AuditTargetReference(
        target_type=AuditTargetType.SKILL_REGISTRY_RECORD,
        target_id=version.skill_id if version else None,
        target_version=version.version if version else None,
        package_hash=version.package_hash if version else None,
        lifecycle_status=version.lifecycle_status.value if version else None,
    )
    status = (
        AuditReportStatus.CONFLICTED
        if projection.outcome == SkillProjectionOutcome.CONFLICT
        else AuditReportStatus.INCOMPLETE
    )
    readiness = derive_decision_readiness(
        audit_type=AuditType.REGISTRY_CONSISTENCY,
        findings=(finding,),
        report_status=status,
        registry_outcome=projection.outcome,
    )
    audit_report = UnifiedAuditReport(
        audit_id=audit_id or uuid4(),
        audit_type=AuditType.REGISTRY_CONSISTENCY,
        target=audit_target,
        status=status,
        overall_severity=_overall_from_findings((finding,)),
        decision_readiness=readiness,
        findings=(finding,),
        source_reports=(
            AuditSourceReference(
                source_system=AuditSourceSystem.SKILL_REGISTRY_PROJECTION,
                source_report_id=projection.reason_code,
                source_version=VALIDATOR_VERSION,
                source_hash=source_hash,
                generated_at=created,
                adapter_version=AUDIT_ADAPTER_VERSION,
            ),
        ),
        blockers=tuple([finding.source_code] if finding.blocking else ()),
        provenance=AuditProvenance(
            generated_by="skill_registry_projection",
            generation_mode=AuditGenerationMode.AUTOMATED_STATIC,
            source_systems=(AuditSourceSystem.SKILL_REGISTRY_PROJECTION,),
            human_review_required=True,
            owner_decision_required=False,
        ),
        generated_at=created,
        adapter_versions={"audit_adapter": AUDIT_ADAPTER_VERSION},
    )
    return audit_report.model_copy(update={"report_hash": compute_report_hash(audit_report)})


def adapt_connector_policy_decision(
    decision: ConnectorPolicyDecision,
    *,
    target: AuditTargetReference,
    audit_id: UUID | None = None,
    generated_at: datetime | None = None,
) -> UnifiedAuditReport:
    created = generated_at or datetime.now(tz=UTC)
    source_hash = hash_source_payload(decision)
    findings: list[AuditFinding] = []

    if decision.outcome != ConnectorPolicyOutcome.ALLOW:
        source_code = decision.reason or decision.outcome.value
        severity = map_connector_policy_outcome(decision.outcome, source_code)
        approval_related = (
            decision.outcome == ConnectorPolicyOutcome.REQUIRE_APPROVAL
            or decision.approval_required
        )
        category = AuditFindingCategory.CONNECTOR_POLICY
        if "tenant" in source_code:
            category = AuditFindingCategory.TENANT_ISOLATION
        if "secret" in source_code or "credential" in source_code:
            category = AuditFindingCategory.CREDENTIAL_BOUNDARY
        if "billing" in source_code:
            category = AuditFindingCategory.BUDGET
        if "approval" in source_code:
            category = AuditFindingCategory.APPROVAL
        blocking, execution_blocking = derive_blocking_flags(
            source_system=AuditSourceSystem.CONNECTOR_POLICY_ENGINE,
            source_code=source_code,
            severity=severity,
            category=category,
            approval_related=approval_related,
        )
        if decision.outcome == ConnectorPolicyOutcome.DENY:
            blocking = True
            execution_blocking = True
            source_code = source_code or "connector_policy_deny"
        findings.append(
            AuditFinding(
                finding_id=_finding_id(AuditSourceSystem.CONNECTOR_POLICY_ENGINE, source_code, 0),
                source_system=AuditSourceSystem.CONNECTOR_POLICY_ENGINE,
                source_code=source_code,
                category=category,
                severity=severity,
                title=source_code.replace("_", " "),
                message=redact_text(decision.reason or decision.outcome.value),
                blocking=blocking,
                execution_blocking=execution_blocking,
                source_payload_hash=source_hash,
                created_at=created,
            )
        )
    else:
        findings.append(
            AuditFinding(
                finding_id=_finding_id(AuditSourceSystem.CONNECTOR_POLICY_ENGINE, "allowed", 0),
                source_system=AuditSourceSystem.CONNECTOR_POLICY_ENGINE,
                source_code="allowed",
                category=AuditFindingCategory.CONNECTOR_POLICY,
                severity=AuditFindingSeverity.INFO,
                title="Policy allowed",
                message="Connector policy evaluation allowed the request.",
                blocking=False,
                execution_blocking=False,
                source_payload_hash=source_hash,
                created_at=created,
            )
        )

    for index, policy_finding in enumerate(decision.findings):
        if policy_finding.passed:
            continue
        code = policy_finding.check_id
        severity = (
            AuditFindingSeverity.ERROR
            if policy_finding.severity == "error"
            else AuditFindingSeverity.WARNING
        )
        blocking, execution_blocking = derive_blocking_flags(
            source_system=AuditSourceSystem.CONNECTOR_POLICY_ENGINE,
            source_code=code,
            severity=severity,
            category=AuditFindingCategory.CONNECTOR_POLICY,
        )
        findings.append(
            AuditFinding(
                finding_id=_finding_id(AuditSourceSystem.CONNECTOR_POLICY_ENGINE, code, index + 1),
                source_system=AuditSourceSystem.CONNECTOR_POLICY_ENGINE,
                source_code=code,
                category=AuditFindingCategory.CONNECTOR_POLICY,
                severity=severity,
                title=code.replace("_", " "),
                message=redact_text(policy_finding.message),
                blocking=blocking,
                execution_blocking=execution_blocking,
                source_payload_hash=source_hash,
                created_at=created,
            )
        )

    status = AuditReportStatus.COMPLETE
    readiness = derive_decision_readiness(
        audit_type=AuditType.CONNECTOR_POLICY,
        findings=tuple(findings),
        report_status=status,
        connector_outcome=decision.outcome,
    )
    audit_report = UnifiedAuditReport(
        audit_id=audit_id or uuid4(),
        audit_type=AuditType.CONNECTOR_POLICY,
        target=target,
        status=status,
        overall_severity=_overall_from_findings(findings),
        decision_readiness=readiness,
        findings=tuple(findings),
        source_reports=(
            AuditSourceReference(
                source_system=AuditSourceSystem.CONNECTOR_POLICY_ENGINE,
                source_report_id=target.target_id or "connector-policy",
                source_version=AUDIT_ADAPTER_VERSION,
                source_hash=source_hash,
                generated_at=created,
                adapter_version=AUDIT_ADAPTER_VERSION,
            ),
        ),
        blockers=tuple(f.source_code for f in findings if f.blocking and not f.resolved),
        recommendations=_recommendations_from_findings(findings),
        provenance=AuditProvenance(
            generated_by="connector_policy_engine",
            generation_mode=AuditGenerationMode.AUTOMATED_POLICY,
            source_systems=(AuditSourceSystem.CONNECTOR_POLICY_ENGINE,),
            human_review_required=decision.approval_required,
            owner_decision_required=decision.approval_required,
        ),
        generated_at=created,
        adapter_versions={"audit_adapter": AUDIT_ADAPTER_VERSION},
    )
    return audit_report.model_copy(update={"report_hash": compute_report_hash(audit_report)})


def adapt_connector_evidence_descriptor(
    descriptor: ConnectorEvidenceDescriptor,
    *,
    target: AuditTargetReference | None = None,
    audit_id: UUID | None = None,
    generated_at: datetime | None = None,
) -> UnifiedAuditReport:
    created = generated_at or descriptor.finished_at
    source_hash = hash_source_payload(descriptor)
    evidence_ref = AuditEvidenceReference(
        evidence_id=str(descriptor.evidence_id),
        evidence_kind="connector_descriptor",
        input_hash=descriptor.input_hash,
        output_hash=descriptor.output_hash,
        provider_metadata_hash=descriptor.provider_metadata_hash,
        lineage_parent_ids=descriptor.lineage_parent_ids,
        external_reference_id=descriptor.external_reference_id,
    )
    audit_target = target or AuditTargetReference(
        target_type=AuditTargetType.CONNECTOR_REQUEST,
        target_id=str(descriptor.request_id),
        connector_id=descriptor.connector_id,
        tool_id=descriptor.tool_id,
        target_version=descriptor.connector_version,
        tenant_id=str(descriptor.tenant_id),
        project_id=str(descriptor.project_id),
    )
    audit_report = UnifiedAuditReport(
        audit_id=audit_id or uuid4(),
        audit_type=AuditType.CONNECTOR_POLICY,
        target=audit_target,
        status=AuditReportStatus.COMPLETE,
        overall_severity=AuditOverallSeverity.INFO,
        decision_readiness=AuditDecisionReadiness.NOT_READY,
        findings=(),
        source_reports=(
            AuditSourceReference(
                source_system=AuditSourceSystem.CONNECTOR_EVIDENCE_DESCRIPTOR,
                source_report_id=str(descriptor.evidence_id),
                source_version=AUDIT_ADAPTER_VERSION,
                source_hash=source_hash,
                generated_at=created,
                adapter_version=AUDIT_ADAPTER_VERSION,
            ),
        ),
        evidence_references=(evidence_ref,),
        provenance=AuditProvenance(
            generated_by="connector_evidence_descriptor",
            generation_mode=AuditGenerationMode.AUTOMATED_POLICY,
            source_systems=(AuditSourceSystem.CONNECTOR_EVIDENCE_DESCRIPTOR,),
            human_review_required=False,
            owner_decision_required=False,
        ),
        generated_at=created,
        adapter_versions={"audit_adapter": AUDIT_ADAPTER_VERSION},
    )
    return audit_report.model_copy(update={"report_hash": compute_report_hash(audit_report)})


def adapt_connector_execution_result_schema_support(
    result: ConnectorExecutionResult,
    *,
    target: AuditTargetReference | None = None,
    audit_id: UUID | None = None,
    generated_at: datetime | None = None,
) -> UnifiedAuditReport:
    created = generated_at or result.finished_at
    source_hash = hash_source_payload(result)
    audit_target = target or AuditTargetReference(
        target_type=AuditTargetType.CONNECTOR_REQUEST,
        target_id=str(result.request_id),
        connector_id=result.connector_id,
        tool_id=result.tool_id,
        target_version=result.connector_version,
    )
    evidence_refs: tuple[AuditEvidenceReference, ...] = ()
    if result.evidence_descriptor is not None:
        descriptor = result.evidence_descriptor
        evidence_refs = (
            AuditEvidenceReference(
                evidence_id=str(descriptor.evidence_id),
                evidence_kind="connector_descriptor",
                input_hash=descriptor.input_hash,
                output_hash=descriptor.output_hash,
                provider_metadata_hash=descriptor.provider_metadata_hash,
                lineage_parent_ids=descriptor.lineage_parent_ids,
                external_reference_id=descriptor.external_reference_id,
            ),
        )
    audit_report = UnifiedAuditReport(
        audit_id=audit_id or uuid4(),
        audit_type=AuditType.CONNECTOR_POLICY,
        target=audit_target,
        status=AuditReportStatus.COMPLETE,
        overall_severity=AuditOverallSeverity.INFO,
        decision_readiness=AuditDecisionReadiness.NOT_READY,
        findings=(),
        source_reports=(
            AuditSourceReference(
                source_system=AuditSourceSystem.CONNECTOR_GATEWAY,
                source_report_id=str(result.request_id),
                source_version=AUDIT_ADAPTER_VERSION,
                source_hash=source_hash,
                generated_at=created,
                adapter_version=AUDIT_ADAPTER_VERSION,
            ),
        ),
        evidence_references=evidence_refs,
        provenance=AuditProvenance(
            generated_by="connector_gateway",
            generation_mode=AuditGenerationMode.AUTOMATED_POLICY,
            source_systems=(AuditSourceSystem.CONNECTOR_GATEWAY,),
            human_review_required=False,
            owner_decision_required=False,
        ),
        generated_at=created,
        adapter_versions={"audit_adapter": AUDIT_ADAPTER_VERSION},
    )
    return audit_report.model_copy(update={"report_hash": compute_report_hash(audit_report)})


def _overall_from_findings(
    findings: list[AuditFinding] | tuple[AuditFinding, ...],
) -> AuditOverallSeverity:
    from app.audit.classifications import derive_overall_severity

    return derive_overall_severity(tuple(findings))


def _recommendations_from_findings(findings: list[AuditFinding]) -> tuple[AuditRecommendation, ...]:
    recommendations: list[AuditRecommendation] = []
    for finding in findings:
        if finding.resolved:
            continue
        rec_type: AuditRecommendationType | None = None
        if finding.source_code.startswith("manifest_"):
            rec_type = AuditRecommendationType.FIX_MANIFEST
        elif finding.source_code in {"secret_file", "security_secret_detected"}:
            rec_type = AuditRecommendationType.REMOVE_FORBIDDEN_FILE
        elif finding.category == AuditFindingCategory.LICENSING:
            rec_type = AuditRecommendationType.VERIFY_LICENSE
        elif finding.category == AuditFindingCategory.PROVENANCE:
            rec_type = AuditRecommendationType.ADD_PROVENANCE
        elif finding.category == AuditFindingCategory.CONFLICT:
            rec_type = AuditRecommendationType.RESOLVE_IDENTITY_CONFLICT
        elif finding.category == AuditFindingCategory.APPROVAL:
            rec_type = AuditRecommendationType.REQUEST_APPROVAL
        elif finding.category == AuditFindingCategory.BUDGET:
            rec_type = AuditRecommendationType.ADD_BUDGET_CONTEXT
        elif finding.category == AuditFindingCategory.IDEMPOTENCY:
            rec_type = AuditRecommendationType.ADD_IDEMPOTENCY_SUPPORT
        elif finding.severity == AuditFindingSeverity.CRITICAL:
            rec_type = AuditRecommendationType.REQUEST_SECURITY_REVIEW
        if rec_type is not None:
            recommendations.append(
                AuditRecommendation(
                    recommendation_type=rec_type,
                    message=finding.message,
                    related_finding_ids=(finding.finding_id,),
                )
            )
    return tuple(recommendations)


# Re-export for serialization module circular import fix
from app.skills.registry_contracts import SkillProjectionOutcome  # noqa: E402
