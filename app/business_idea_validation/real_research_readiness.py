"""REAL-RESEARCH-READINESS — automated gates for live provider research quality."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from app.business_idea_validation.evidence_validation import is_valid_source_url
from app.business_idea_validation.report_export import build_customer_report_txt, validate_export_content
from app.core.config import Settings
from app.schemas.contracts import (
    BivRunObservability,
    BusinessIdeaValidationOutput,
)

_DOM_MARKERS = (
    "to main content",
    "skip to navigation",
    "cookie policy",
    "javascript is disabled",
    "<div",
    "<script",
    "document.getelementbyid",
)
_VERDICT_VAGUE = re.compile(
    r"идея перспективн|надо проверить$|требует дополнительной проверк",
    re.I,
)
_SINGLE_QUERY_MIN_DISTINCT = 4


@dataclass(slots=True)
class RealResearchValidationResult:
    passed: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


def validate_query_decomposition(output: BusinessIdeaValidationOutput) -> list[str]:
    violations: list[str] = []
    plan = output.research_plan or []
    queries = [p.query.strip() for p in plan if (p.query or "").strip()]
    if len(queries) < _SINGLE_QUERY_MIN_DISTINCT:
        violations.append(f"too_few_queries:{len(queries)}")
    distinct = {q.lower() for q in queries}
    if len(distinct) < _SINGLE_QUERY_MIN_DISTINCT:
        violations.append("queries_not_distinct")
    if len(queries) == 1 and len(queries[0]) > 120:
        violations.append("single_long_query_string")
    return violations


def validate_evidence_integrity(output: BusinessIdeaValidationOutput) -> list[str]:
    violations: list[str] = []
    accepted_ids = {e.evidence_id for e in (output.evidence_items or []) if e.accepted}
    rejected_ids = {e.evidence_id for e in (output.evidence_items or []) if not e.accepted}

    for item in output.evidence_items or []:
        if not item.accepted:
            continue
        if not is_valid_source_url(item.source_url):
            violations.append(f"empty_evidence_url:{item.evidence_id}")
        if not (item.excerpt or "").strip():
            violations.append(f"empty_excerpt:{item.evidence_id}")
        if not (item.claim_supported or "").strip():
            violations.append(f"empty_claim:{item.evidence_id}")
        blob = f"{item.excerpt} {item.claim_supported}".lower()
        if any(marker in blob for marker in _DOM_MARKERS):
            violations.append(f"raw_dom_in_evidence:{item.evidence_id}")

    for finding in output.finding_items or []:
        if not finding.evidence_ids:
            violations.append(f"finding_without_evidence:{finding.finding_id}")
            continue
        for eid in finding.evidence_ids:
            if eid in rejected_ids:
                violations.append(f"finding_uses_rejected_evidence:{finding.finding_id}")
            if eid not in accepted_ids:
                violations.append(f"finding_unaccepted_evidence:{finding.finding_id}")

    for finding in output.findings or []:
        if finding.is_hypothesis:
            continue
        if not finding.linked_evidence_ids:
            violations.append(f"legacy_finding_without_evidence:{finding.category}")

    return violations


def validate_customer_report(output: BusinessIdeaValidationOutput) -> list[str]:
    if output.customer_report is None:
        return ["customer_report_missing"]
    violations: list[str] = []
    report = output.customer_report
    if report.executive_summary is None or report.coverage is None:
        violations.append("report_sections_incomplete")
    if output.commercial_verdict is None:
        violations.append("commercial_verdict_missing")
    elif _VERDICT_VAGUE.search(output.commercial_verdict.rationale or ""):
        violations.append("verdict_too_vague")
    elif len((output.commercial_verdict.rationale or "").strip()) < 40:
        violations.append("verdict_rationale_too_short")
    return violations


def validate_minimum_real_research(output: BusinessIdeaValidationOutput) -> list[str]:
    """Hard gates for REAL-RESEARCH-READINESS — not satisfied by empty success."""
    violations: list[str] = []
    accepted = [e for e in (output.evidence_items or []) if e.accepted]
    if len(accepted) < 3:
        violations.append(f"fewer_than_3_accepted_sources:{len(accepted)}")
    confirmed_findings = [f for f in (output.finding_items or []) if f.evidence_ids]
    if len(confirmed_findings) < 1:
        violations.append("no_evidence_linked_findings")
    if (output.mcp_search_calls or 0) > 0 and (output.mcp_fetch_calls or 0) == 0:
        violations.append("search_without_successful_fetch")
    return violations


def validate_export(output: BusinessIdeaValidationOutput) -> list[str]:
    if output.customer_report is None:
        return ["export_source_missing"]
    text = build_customer_report_txt(report=output.customer_report, output=output)
    return validate_export_content(text)


def validate_budgets(
    observability: BivRunObservability | None,
    settings: Settings,
) -> list[str]:
    if observability is None:
        return ["observability_missing"]
    violations: list[str] = []
    if observability.search_count > settings.biv_research_max_search_calls:
        violations.append("search_budget_exceeded")
    if observability.fetch_count > settings.biv_research_max_fetch_calls:
        violations.append("fetch_budget_exceeded")
    if observability.total_latency_ms is not None:
        max_ms = int(settings.biv_research_max_latency_seconds * 1000)
        if observability.total_latency_ms > max_ms:
            violations.append("latency_budget_exceeded")
    est_cost = estimate_provider_cost(observability)
    if est_cost > settings.biv_research_max_estimated_cost_usd:
        violations.append("cost_budget_exceeded")
    return violations


def estimate_provider_cost(observability: BivRunObservability) -> float:
    """Conservative USD estimate — search + fetch only (no LLM in BIV pipeline)."""
    search_cost = observability.search_count * 0.002
    fetch_cost = observability.fetch_count * 0.01
    return round(search_cost + fetch_cost, 4)


def collect_run_metrics(
    output: BusinessIdeaValidationOutput,
    observability: BivRunObservability | None,
) -> dict[str, Any]:
    accepted = [e for e in (output.evidence_items or []) if e.accepted]
    rejected = [e for e in (output.evidence_items or []) if not e.accepted]
    findings = [f for f in (output.finding_items or []) if f.evidence_ids]
    return {
        "accepted_sources": len(accepted) or len(
            [s for s in (output.sources or []) if s.url]
        ),
        "rejected_sources": len(rejected),
        "findings": len(findings) or len([f for f in (output.findings or []) if not f.is_hypothesis]),
        "verdict": (
            output.commercial_verdict.kind.value
            if output.commercial_verdict
            else (output.verdict.value if output.verdict else None)
        ),
        "confidence": output.confidence.total_score if output.confidence else None,
        "coverage": observability.coverage if observability else None,
        "search_count": observability.search_count if observability else output.mcp_search_calls,
        "fetch_count": observability.fetch_count if observability else output.mcp_fetch_calls,
        "total_latency_ms": observability.total_latency_ms if observability else None,
        "estimated_cost_usd": estimate_provider_cost(observability) if observability else None,
        "provider_errors": list(observability.provider_errors) if observability else [],
    }


def validate_run_output(
    output: BusinessIdeaValidationOutput,
    *,
    observability: BivRunObservability | None = None,
    settings: Settings | None = None,
) -> RealResearchValidationResult:
    blockers: list[str] = []
    warnings: list[str] = []

    blockers.extend(validate_minimum_real_research(output))
    blockers.extend(validate_query_decomposition(output))
    blockers.extend(validate_evidence_integrity(output))
    blockers.extend(validate_customer_report(output))
    export_violations = validate_export(output)
    blockers.extend(export_violations)

    if output.research_terminal_state and output.research_terminal_state.value == "failed":
        blockers.append("research_terminal_failed")

    if settings and observability:
        budget_violations = validate_budgets(observability, settings)
        blockers.extend(budget_violations)

    if not output.sources:
        warnings.append("no_sources_collected")

    metrics = collect_run_metrics(output, observability)
    return RealResearchValidationResult(
        passed=not blockers,
        blockers=blockers,
        warnings=warnings,
        metrics=metrics,
    )


def provider_smoke_passed(probe_payload: dict[str, Any]) -> tuple[bool, str | None]:
    if probe_payload.get("mock_providers"):
        return False, "mock_providers_enabled"
    if probe_payload.get("probe_skipped"):
        return False, str(probe_payload["probe_skipped"])
    fetch_contour = probe_payload.get("fetch_contour") or {}
    if fetch_contour.get("pass") is True:
        return True, None
    status = str(probe_payload.get("status") or "")
    if status not in {"ready", "partially_ready"}:
        providers = probe_payload.get("providers") or {}
        codes = [
            str(p.get("safe_error_code") or p.get("state"))
            for p in providers.values()
        ]
        return False, f"provider_status_{status}:{','.join(codes)}"
    # Search-only partially_ready without fetch contour is insufficient for real research.
    if fetch_contour.get("pass") is False:
        return False, str(fetch_contour.get("blocked_reason") or "fetch_contour_unavailable")
    return True, None


def format_control_summary(
    *,
    provider_status: str,
    case_status: str,
    validation: RealResearchValidationResult,
    export_pass: bool,
) -> str:
    m = validation.metrics
    latency_sec = (
        round(m["total_latency_ms"] / 1000, 1) if m.get("total_latency_ms") else "—"
    )
    cost = m.get("estimated_cost_usd")
    lines = [
        f"Real providers: {provider_status}",
        f"Marketsynth case: {case_status}",
        f"Accepted sources: {m.get('accepted_sources', 0)}",
        f"Rejected sources: {m.get('rejected_sources', 0)}",
        f"Findings: {m.get('findings', 0)}",
        f"Verdict: {m.get('verdict', '—')}",
        f"Confidence: {m.get('confidence', '—')}%",
        f"Coverage: {m.get('coverage', '—')}%",
        f"Latency: {latency_sec} sec",
        f"Cost: ${cost if cost is not None else '—'}",
        f"Raw DOM: {sum(1 for b in validation.blockers if 'raw_dom' in b)}",
        f"Empty URLs: {sum(1 for b in validation.blockers if 'empty_evidence_url' in b)}",
        f"Unsupported claims: {sum(1 for b in validation.blockers if 'finding_without_evidence' in b)}",
        f"Export: {'PASS' if export_pass else 'FAIL'}",
    ]
    if validation.blockers:
        lines.append(f"Blockers: {', '.join(validation.blockers[:8])}")
    return "\n".join(lines)


def count_export_url_issues(text: str) -> int:
    issues = 0
    for line in text.splitlines():
        if "http://" in line or "https://" in line:
            for token in line.split():
                if token.startswith("http"):
                    url = token.rstrip(").,;")
                    parsed = urlparse(url)
                    if not parsed.netloc:
                        issues += 1
    return issues
