"""Pattern source support gate — pure validation, no I/O."""

from __future__ import annotations

from typing import Any

from app.knowledge.workflow_patterns.contracts import ManualAuditRecord, SourceSupportResult

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


def _catalog_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["workflow_template_id"]: item for item in catalog.get("templates", [])}


def _has_critical_finding(template: dict[str, Any]) -> bool:
    for finding in template.get("security_findings", []):
        if finding.get("finding_type") in CRITICAL_FINDINGS:
            return True
        if finding.get("severity") == "critical":
            return True
    return False


def _audit_covers_workflow(
    audits: list[ManualAuditRecord],
    workflow_id: str,
    pattern_id: str,
) -> ManualAuditRecord | None:
    for audit in audits:
        if workflow_id not in audit.workflow_template_ids:
            continue
        if pattern_id not in audit.pattern_ids:
            continue
        if audit.decision in {"approved_for_pilot", "approved_for_core"}:
            return audit
    return None


def validate_pattern_source_support(
    pattern: dict[str, Any],
    catalog: dict[str, Any],
    audit_records: list[ManualAuditRecord],
) -> SourceSupportResult:
    pattern_id = str(pattern.get("pattern_id", ""))
    source_ids = list(pattern.get("source_workflow_ids") or [])
    reasons: list[str] = []
    blockers: list[str] = []

    if not source_ids:
        blockers.append("zero_source_pattern")
        return SourceSupportResult(
            supported=False,
            support_mode="unsupported",
            reasons=reasons,
            blockers=blockers,
        )

    index = _catalog_index(catalog)
    valid_sources: list[str] = []

    for source_id in source_ids:
        template = index.get(source_id)
        if template is None:
            blockers.append(f"source_missing_from_catalog:{source_id}")
            continue
        if template.get("quarantine_status") == "rejected":
            blockers.append(f"source_rejected:{source_id}")
            continue
        if template.get("adaptation_status") == "rejected":
            blockers.append(f"source_adaptation_rejected:{source_id}")
            continue
        if _has_critical_finding(template):
            blockers.append(f"source_critical_finding:{source_id}")
            continue
        expected_hash = template.get("workflow_hash")
        if expected_hash and len(expected_hash) == 64:
            reasons.append(f"source_hash_verified:{source_id}")
        valid_sources.append(source_id)

    if blockers:
        return SourceSupportResult(
            supported=False,
            support_mode="unsupported",
            reasons=reasons,
            blockers=blockers,
        )

    unique_sources = sorted(set(valid_sources))
    if len(unique_sources) >= 2:
        reasons.append("two_distinct_source_workflows")
        return SourceSupportResult(
            supported=True,
            support_mode="two_source",
            reasons=reasons,
            blockers=[],
        )

    if len(unique_sources) == 1:
        audit = _audit_covers_workflow(audit_records, unique_sources[0], pattern_id)
        if audit is None:
            blockers.append("single_source_without_manual_audit")
            return SourceSupportResult(
                supported=False,
                support_mode="unsupported",
                reasons=reasons,
                blockers=blockers,
            )
        reasons.append(f"manual_audit:{audit.audit_id}")
        reasons.append(audit.rationale)
        return SourceSupportResult(
            supported=True,
            support_mode="single_source_audited",
            reasons=reasons,
            blockers=[],
        )

    blockers.append("no_valid_sources")
    return SourceSupportResult(
        supported=False,
        support_mode="unsupported",
        reasons=reasons,
        blockers=blockers,
    )
