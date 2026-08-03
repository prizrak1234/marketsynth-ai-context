"""Deterministic catalog search — no LLM, no vector DB."""

from __future__ import annotations

from app.knowledge.catalog.contracts import CatalogSearchResult, RecommendedAction
from app.knowledge.catalog.visibility import filter_by_tenant, is_audit_mode


def _recommended_action(record: dict) -> RecommendedAction:
    if record.get("adaptation_status") == "rejected":
        return "reject"
    if record.get("security_findings"):
        return "request_security_review"
    if record.get("artifact_type") == "workflow_template":
        return "adapt_workflow_pattern"
    return "review_methodology"


def search_artifacts(
    index: list[dict],
    *,
    query: str | None = None,
    artifact_type: str | None = None,
    capability: str | None = None,
    tenant_id: str = "global",
    mode: str = "internal_audit",
) -> list[CatalogSearchResult]:
    audit = is_audit_mode(mode)
    visible = filter_by_tenant(index, tenant_id=tenant_id, audit_mode=audit)
    q = (query or "").lower().strip()
    results: list[CatalogSearchResult] = []
    for record in visible:
        if artifact_type and record.get("artifact_type") != artifact_type:
            continue
        if capability and capability not in record.get("capabilities", []):
            continue
        matching: list[str] = []
        if q:
            for field in ("title", "summary", "category"):
                val = str(record.get(field, "")).lower()
                if q in val:
                    matching.append(field)
            if not matching and q not in str(record.get("node_types", [])).lower():
                continue
        elif not q:
            matching.append("filter_match")
        results.append(
            CatalogSearchResult(
                artifact_id=record["artifact_id"],
                title=record["title"],
                artifact_type=record["artifact_type"],
                summary=record.get("summary", ""),
                capabilities=record.get("capabilities", []),
                source=record.get("source", "unknown"),
                trust_status=record.get("trust_status", "quarantined"),
                adaptation_status=record.get("adaptation_status", "catalog_only"),
                security_findings=record.get("security_findings", []),
                matching_fields=matching,
                ranking_explanation="deterministic_token_filter",
                recommended_action=_recommended_action(record),
            )
        )
    return sorted(results, key=lambda r: r.artifact_id)
