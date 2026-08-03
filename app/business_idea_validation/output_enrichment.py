"""CWF.1 — enrich persisted BIV output with commercial + internal reports."""

from __future__ import annotations

from app.business_idea_validation.commercial_verdict import (
    build_commercial_verdict,
    map_legacy_verdict_kind,
)
from app.business_idea_validation.customer_report import build_customer_research_report
from app.business_idea_validation.evidence_contract import build_evidence_items, build_finding_items
from app.business_idea_validation.gap_presentation import present_research_gaps
from app.business_idea_validation.internal_report import build_internal_research_diagnostics
from app.business_idea_validation.research_cascade import phases_completed
from app.business_idea_validation.findings import build_findings
from app.schemas.contracts import (
    BivResearchResultKind,
    BivResearchTerminalState,
    BusinessIdeaValidationInput,
    BusinessIdeaValidationOutput,
)

_TERMINAL_STATES = {
    BivResearchTerminalState.SUCCEEDED_COMPLETE,
    BivResearchTerminalState.SUCCEEDED_INSUFFICIENT,
    BivResearchTerminalState.FAILED,
}


def enrich_output_gap_presentation(
    output: BusinessIdeaValidationOutput,
) -> BusinessIdeaValidationOutput:
    """Backfill customer-safe gap items for runs persisted before 01.3B.1."""
    if output.research_gap_items:
        return output
    codes = list(output.research_gaps)
    if output.business_verdict_id is None and "business_verdict_missing" not in codes:
        codes.append("business_verdict_missing")
    if not codes:
        return output
    return output.model_copy(update={"research_gap_items": present_research_gaps(codes)})


def enrich_output_commercial(
    output: BusinessIdeaValidationOutput,
    inp: BusinessIdeaValidationInput | None = None,
) -> BusinessIdeaValidationOutput:
    """Backfill customer_report + internal_diagnostics for legacy persisted runs."""
    enriched = enrich_output_gap_presentation(output)
    if enriched.result_kind == BivResearchResultKind.PARTIAL_RESEARCH:
        return enriched
    if enriched.customer_report is not None and enriched.internal_diagnostics is not None:
        return enriched

    has_material = bool(
        enriched.findings
        or enriched.category_coverage
        or enriched.evidence
        or enriched.partial_report
        or enriched.risks
        or enriched.research_gaps
        or enriched.research_plan
        or enriched.sources
        or enriched.research_terminal_state in _TERMINAL_STATES
    )
    if not has_material:
        return enriched

    if inp is None:
        idea = "Коммерческое исследование Marketsynth"
        if enriched.partial_report and enriched.partial_report.established_findings:
            idea = enriched.partial_report.established_findings[0][:800]
        inp = BusinessIdeaValidationInput(
            tenant_id=enriched.owner_id or enriched.investigation_id,
            project_id=enriched.project_id or enriched.investigation_id,
            user_request_id=enriched.investigation_id,
            idea=idea if len(idea) >= 8 else f"{idea} — контекст проекта",
        )

    findings = [f for f in enriched.findings if not f.is_hypothesis]
    if not findings and enriched.evidence:
        findings = build_findings(enriched.evidence, inp=inp)

    gate_passed = enriched.business_verdict_id is not None
    phases = phases_completed(enriched.research_plan)

    customer_report = enriched.customer_report
    if customer_report is None:
        customer_report = build_customer_research_report(
            inp=inp,
            findings=findings,
            evidence=enriched.evidence,
            risks=enriched.risks,
            category_coverage=enriched.category_coverage,
            plan_items=enriched.research_plan,
            confidence=enriched.confidence,
            gate_passed=gate_passed,
            verdict=enriched.verdict,
            phases_executed=phases,
        )

    internal = enriched.internal_diagnostics
    if internal is None:
        internal = build_internal_research_diagnostics(
            plan_items=enriched.research_plan,
            raw_research_gaps=enriched.research_gaps,
            raw_limitations=enriched.limitations,
            category_coverage=enriched.category_coverage,
            confidence=enriched.confidence,
            phases_executed=phases,
            mcp_search_calls=enriched.mcp_search_calls,
            mcp_fetch_calls=enriched.mcp_fetch_calls,
            research_rounds_completed=enriched.research_rounds_completed,
            tool_call_audit_ids=enriched.tool_call_audit_ids,
            evidence=enriched.evidence,
            sources=enriched.sources,
            stop_reason=enriched.research_stop_reason,
            coverage_plan=enriched.coverage_plan,
            partial_report=enriched.partial_report,
            gap_items=enriched.research_gap_items,
        )

    return enriched.model_copy(
        update={
            "customer_report": customer_report,
            "internal_diagnostics": internal,
            **_commercial_contract_backfill(enriched, inp, findings, gate_passed),
        },
    )


def _commercial_contract_backfill(
    enriched: BusinessIdeaValidationOutput,
    inp: BusinessIdeaValidationInput,
    findings: list,
    gate_passed: bool,
) -> dict:
    """Backfill evidence_items, finding_items, commercial_verdict for legacy runs."""
    updates: dict = {}
    if not enriched.evidence_items and enriched.evidence:
        updates["evidence_items"] = build_evidence_items(enriched.evidence)
    evidence_items = updates.get("evidence_items") or enriched.evidence_items
    if not enriched.finding_items and findings and evidence_items:
        updates["finding_items"] = build_finding_items(enriched.findings, evidence_items)
    if enriched.commercial_verdict is None:
        accepted = [e for e in evidence_items if e.accepted] if evidence_items else []
        commercial_kind = map_legacy_verdict_kind(
            enriched.verdict,
            gate_passed=gate_passed,
            confidence=enriched.confidence.total_score,
            confirmed_count=len(accepted),
        )
        unconfirmed = [
            g.customer_message for g in enriched.research_gap_items[:6]
        ] or enriched.limitations[:6]
        updates["commercial_verdict"] = build_commercial_verdict(
            kind=commercial_kind,
            confidence=enriched.confidence.total_score,
            findings=findings,
            risks=enriched.risks,
            unconfirmed_topics=unconfirmed,
            gate_passed=gate_passed,
        )
    return updates
