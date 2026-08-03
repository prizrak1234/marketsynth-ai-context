"""Strict reusable pattern candidate gate — metadata only."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.knowledge.workflow_catalog.classifiers import ClassificationResult
from app.knowledge.workflow_catalog.contracts import AdaptationStatus, WorkflowTemplateRecord

CRITICAL_FINDINGS = frozenset(
    {
        "embedded_api_key",
        "bearer_token",
        "private_key",
        "password_marker",
        "shell_command_node",
        "shell_delete",
        "destructive_sql",
    }
)
SECRET_FINDINGS = CRITICAL_FINDINGS | frozenset({"oauth_token_marker", "api_key_marker"})
HIGH_RISK_COMMUNITY = frozenset({"community_node"})


@dataclass(frozen=True)
class CandidateEvaluation:
    adaptation_status: AdaptationStatus
    candidate_reasons: list[str] = field(default_factory=list)
    candidate_blockers: list[str] = field(default_factory=list)
    manual_audit_required: bool = True


def evaluate_candidate_eligibility(
    record: WorkflowTemplateRecord,
    classification: ClassificationResult,
    *,
    is_unique_or_canonical: bool = True,
    use_case_identifiable: bool = True,
    metadata_complete: bool = True,
) -> CandidateEvaluation:
    reasons: list[str] = []
    blockers: list[str] = []

    if record.quarantine_status != "quarantined":
        blockers.append("not_quarantined")

    if not is_unique_or_canonical:
        blockers.append("non_canonical_duplicate_member")

    if record.destructive_actions or record.shell_nodes:
        blockers.append("destructive_or_shell")

    if record.categories == ["other"]:
        blockers.append("capability_other_only")

    if classification.capability_confidence == "low":
        blockers.append("low_capability_confidence")

    if classification.priority_confidence == "low":
        blockers.append("low_priority_confidence")

    if not use_case_identifiable or not record.use_case.strip():
        blockers.append("use_case_not_identifiable")

    if not metadata_complete:
        blockers.append("metadata_incomplete")

    if not record.node_types or len(record.node_types) < 2:
        blockers.append("topology_not_meaningful")

    if not record.provenance.get("source_id"):
        blockers.append("missing_source_provenance")

    for finding in record.security_findings:
        if finding.finding_type in CRITICAL_FINDINGS:
            blockers.append(f"critical_finding:{finding.finding_type}")
        if finding.finding_type in SECRET_FINDINGS:
            blockers.append(f"exposed_secret:{finding.finding_type}")
        if finding.finding_type in HIGH_RISK_COMMUNITY and finding.severity in {"high", "critical"}:
            blockers.append("unknown_high_risk_community_node")

    sensitive = record.publication_actions or record.billing_actions
    if record.personal_data_risk in {"elevated", "high"}:
        sensitive = True

    if record.code_nodes:
        blockers.append("code_node_present")

    if sensitive:
        reasons.append("sensitive_workflow_requires_manual_security_review")
        reasons.append("mandatory_security_review_before_pattern_extraction")

    if blockers:
        status: AdaptationStatus = "requires_rewrite" if (
            record.destructive_actions or record.shell_nodes
        ) else "catalog_only"
        return CandidateEvaluation(
            adaptation_status=status,
            candidate_reasons=reasons,
            candidate_blockers=sorted(set(blockers)),
            manual_audit_required=True,
        )

    reasons.extend(
        [
            "valid_n8n_export",
            "unique_or_canonical",
            "no_critical_security_blockers",
            "capability_confidence_sufficient",
            "topology_meaningful",
            "provenance_present",
            "metadata_complete",
            "manual_audit_required",
        ]
    )
    if classification.capability_confidence == "high":
        reasons.append("high_capability_confidence")
    if len(classification.explanation) >= 2:
        reasons.append("multi_source_classification")

    return CandidateEvaluation(
        adaptation_status="reusable_pattern_candidate",
        candidate_reasons=reasons,
        candidate_blockers=[],
        manual_audit_required=True,
    )
