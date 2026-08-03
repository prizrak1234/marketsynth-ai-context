"""Deterministic audit report serialization and hashing (SKILL-01.6)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.audit.contracts import AuditFinding, UnifiedAuditReport


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported type for canonical JSON: {type(value)!r}")


def canonical_model_dict(model: BaseModel) -> dict[str, Any]:
    return json.loads(canonical_json(model.model_dump(mode="json")))


def finding_sort_key(finding: AuditFinding) -> tuple[str, ...]:
    return (
        finding.source_system.value,
        finding.source_code,
        finding.location or "",
        finding.finding_id,
        finding.source_payload_hash or "",
    )


def sorted_findings(findings: tuple[AuditFinding, ...]) -> tuple[AuditFinding, ...]:
    return tuple(sorted(findings, key=finding_sort_key))


def deduplication_key(finding: AuditFinding, *, target_id: str | None = None) -> tuple[str, ...]:
    return (
        finding.source_system.value,
        finding.source_code,
        finding.location or "",
        target_id or "",
        finding.source_payload_hash or "",
    )


def deduplicate_findings(
    findings: tuple[AuditFinding, ...],
    *,
    target_id: str | None = None,
) -> tuple[AuditFinding, ...]:
    seen: set[tuple[str, ...]] = set()
    unique: list[AuditFinding] = []
    for finding in sorted_findings(findings):
        key = deduplication_key(finding, target_id=target_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return tuple(unique)


def compute_report_hash(report: UnifiedAuditReport, *, exclude_generated_at: bool = True) -> str:
    payload = canonical_model_dict(report)
    payload.pop("audit_id", None)
    if exclude_generated_at:
        payload.pop("generated_at", None)
    payload.pop("report_hash", None)
    for finding in payload.get("findings", []):
        finding.pop("created_at", None)
    for source_report in payload.get("source_reports", []):
        source_report.pop("generated_at", None)
    findings = payload.get("findings", [])
    payload["findings"] = sorted(
        findings,
        key=lambda item: (
            item["source_system"],
            item["source_code"],
            item.get("location") or "",
            item["finding_id"],
            item.get("source_payload_hash") or "",
        ),
    )
    encoded = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def serialize_report(report: UnifiedAuditReport) -> str:
    return canonical_json(canonical_model_dict(report))
