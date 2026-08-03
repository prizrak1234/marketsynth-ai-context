#!/usr/bin/env python3
"""Scaffold MV 0.2.0 fixtures — run once during SKILL-02.6B setup."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "skills"
    / "ms.skill.market_validation"
    / "0.2.0"
)
FIX = ROOT / "tests" / "fixtures"

PMC_HASH = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
MR_HASH = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
CA_HASH = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
ICP_HASH = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
CIM_HASH = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
CIM_URI = (
    "https://schemas.marketsynth.ai/customer-intelligence/0.1.0/"
    "customer-intelligence.schema.json"
)
PROV = {"skill_id": "ms.skill.market_validation", "skill_version": "0.2.0"}


def upstream_ref(skill_id: str, version: str, out_hash: str, **extra: object) -> dict:
    ref = {
        "source_skill_id": skill_id,
        "source_skill_version": version,
        "source_output_hash": out_hash,
        "source_status": extra.get("source_status", "complete"),
        "source_evidence_references": extra.get(
            "source_evidence_references", ["ev-upstream-001"]
        ),
        "source_unknowns": extra.get("source_unknowns", []),
        "source_conflicts": extra.get("source_conflicts", []),
    }
    optional_keys = (
        "context_id",
        "readiness",
        "research_id",
        "research_status",
        "analysis_id",
    )
    ref.update({k: v for k, v in extra.items() if k in optional_keys})
    return ref


def cim_input_ref(**overrides: object) -> dict:
    base = {
        "source_skill_id": "ms.skill.icp_segmentation",
        "source_skill_version": "0.1.0",
        "source_output_hash": ICP_HASH,
        "cim_schema_uri": CIM_URI,
        "cim_version": "0.1.0",
        "cim_document_hash": CIM_HASH,
        "cim_id": "cim-001",
        "selected_segment_ids": ["seg-remote-eng"],
        "source_status": "ready_for_downstream_use",
        "source_evidence_references": ["ev-seg-seg-remote-eng"],
        "source_unknowns": [{"domain": "budget", "description": "Budget bands unverified"}],
        "source_conflicts": [],
        "provenance": {"submitted_by": "fixture"},
    }
    base.update(overrides)
    return base


def input_base(**overrides: object) -> dict:
    base = {
        "product_marketing_context": upstream_ref(
            "ms.skill.product_marketing_context",
            "0.2.0",
            PMC_HASH,
            context_id="ctx-001",
            readiness="ready",
        ),
        "market_research_output": upstream_ref(
            "ms.skill.market_research",
            "0.1.0",
            MR_HASH,
            research_id="mr-001",
            research_status="complete",
        ),
        "competitor_analysis_output": upstream_ref(
            "ms.skill.competitor_analysis",
            "0.1.0",
            CA_HASH,
            analysis_id="ca-001",
            research_status="complete",
        ),
        "customer_intelligence_reference": cim_input_ref(),
        "validation_objectives": ["Assess commercial viability for async SaaS launch"],
        "declared_business_scope": "B2B async collaboration SaaS",
        "geography": "US, EU",
        "business_model": "subscription",
        "provenance": {"submitted_by": "fixture"},
    }
    base.update(overrides)
    return base


def dimension(dimension: str, status: str = "supportive", **extra: object) -> dict:
    return {
        "dimension": dimension,
        "status": status,
        "evidence_references": extra.get("evidence_references", ["ev-upstream-001"]),
        "contradictory_evidence": extra.get("contradictory_evidence", []),
        "assumptions": extra.get("assumptions", []),
        "unknowns": extra.get("unknowns", []),
        "confidence": extra.get("confidence", "medium"),
        "blockers": extra.get("blockers", []),
        "provenance": PROV,
        **{k: v for k, v in extra.items() if k == "notes"},
    }


def all_dimensions(**overrides: dict[str, dict]) -> list[dict]:
    names = [
        "product_context_quality",
        "market_evidence_quality",
        "customer_evidence_quality",
        "demand_signal_strength",
        "competitor_pressure",
        "segment_fit",
        "reachability",
        "budget_fit",
        "pricing_plausibility",
        "operational_feasibility",
        "switching_difficulty",
        "evidence_coverage",
        "contradiction_severity",
        "regulatory_or_external_constraints",
        "critical_risks",
    ]
    return [dimension(n, **overrides.get(n, {})) for n in names]


def readiness(readiness: str, **extra: object) -> dict:
    return {
        "readiness": readiness,
        "supporting_reasons": extra.get("supporting_reasons", ["Upstream refs complete"]),
        "blockers": extra.get("blockers", []),
        "missing_inputs": extra.get("missing_inputs", []),
        "unresolved_conflicts": extra.get("unresolved_conflicts", []),
        "evidence_coverage": extra.get("evidence_coverage", "partial"),
        "provenance": PROV,
    }


def trace(statement: str, trace_type: str = "evidence", **extra: object) -> dict:
    item = {"statement": statement, "trace_type": trace_type}
    if trace_type == "evidence":
        item["evidence_class"] = extra.get("evidence_class", "market_source")
        item["source_reference"] = extra.get("source_reference", "ev-upstream-001")
    return item


def blocker(
    blocker_code: str,
    *,
    category: str,
    description: str,
    remediation_type: str = "none",
    blocking: bool = True,
    recommended_verdict_effect: str = "stop",
    evidence_references: list[str] | None = None,
) -> dict:
    return {
        "blocker_id": f"blk-{blocker_code.lower()}",
        "blocker_code": blocker_code,
        "category": category,
        "description": description,
        "evidence_references": (
            ["ev-upstream-001"] if evidence_references is None else evidence_references
        ),
        "contradictory_evidence": [],
        "remediation_type": remediation_type,
        "remediation_possible": remediation_type != "none",
        "required_change": "",
        "recommended_verdict_effect": recommended_verdict_effect,
        "severity": "critical",
        "blocking": blocking,
        "owner_review_required": True,
        "provenance": PROV,
    }


def condition(**fields: object) -> dict:
    base = {
        "condition_id": "cond-budget-validation",
        "category": "evidence",
        "statement": "Validate budget bands for target segment",
        "required_action": "Collect pricing interviews",
        "owner": "customer",
        "deadline_or_gate": "before positioning",
        "evidence_required": "3 pricing interviews",
        "blocking": True,
        "validation_method": "review transcripts",
        "status": "open",
        "provenance": PROV,
    }
    base.update(fields)
    return base


def risk(risk_id: str, domain: str, *, severity: str = "moderate", blocking: bool = False) -> dict:
    return {
        "risk_id": risk_id,
        "domain": domain,
        "description": f"Risk in {domain} domain",
        "likelihood": "medium",
        "impact": "moderate",
        "severity": severity,
        "evidence_references": ["ev-upstream-001"],
        "assumptions": [],
        "mitigations": [],
        "residual_risk": "moderate",
        "blocking": blocking,
        "owner_review_required": False,
        "provenance": PROV,
    }


def output_base(**overrides: object) -> dict:
    base = {
        "validation_id": "mv-020-001",
        "skill_id": "ms.skill.market_validation",
        "skill_version": "0.2.0",
        "source_context_reference": upstream_ref(
            "ms.skill.product_marketing_context", "0.2.0", PMC_HASH
        ),
        "source_research_reference": upstream_ref(
            "ms.skill.market_research", "0.1.0", MR_HASH
        ),
        "source_competitor_reference": upstream_ref(
            "ms.skill.competitor_analysis", "0.1.0", CA_HASH
        ),
        "source_cim_reference": {
            "source_skill_id": "ms.skill.icp_segmentation",
            "source_skill_version": "0.1.0",
            "source_output_hash": ICP_HASH,
            "cim_schema_uri": CIM_URI,
            "cim_version": "0.1.0",
            "cim_document_hash": CIM_HASH,
            "selected_segment_ids": ["seg-remote-eng"],
            "source_evidence_references": ["ev-seg-seg-remote-eng"],
            "source_unknowns": [{"domain": "budget", "description": "Budget bands unverified"}],
            "source_conflicts": [],
        },
        "decision_readiness": readiness("ready_for_decision", evidence_coverage="full"),
        "verdict": "proceed",
        "verdict_confidence": "high",
        "executive_summary": (
            "Evidence supports proceeding to positioning for remote engineering SaaS."
        ),
        "decision_dimensions": all_dimensions(),
        "supporting_evidence": [
            trace("Market demand signals support remote async collaboration need.")
        ],
        "contradictory_evidence": [],
        "assumptions": [],
        "inferences": [],
        "unknowns": [{"domain": "budget", "description": "Budget bands unverified"}],
        "conflicts": [],
        "evidence_gaps": [],
        "critical_risks": [],
        "noncritical_risks": [risk("risk-competition", "competitor")],
        "conditions": [],
        "blockers": [],
        "required_changes": [],
        "next_validation_steps": ["Proceed to positioning with selected segment"],
        "recommended_next_stage": "positioning",
        "human_approval_required": True,
        "approval_granted": False,
        "provenance": {
            "skill_id": "ms.skill.market_validation",
            "skill_version": "0.2.0",
            "methodology_ref": "SKILL-02.6B",
            "source_context_skill_id": "ms.skill.product_marketing_context",
            "source_context_skill_version": "0.2.0",
            "source_context_output_hash": PMC_HASH,
            "source_research_skill_id": "ms.skill.market_research",
            "source_research_skill_version": "0.1.0",
            "source_research_output_hash": MR_HASH,
            "source_competitor_skill_id": "ms.skill.competitor_analysis",
            "source_competitor_skill_version": "0.1.0",
            "source_competitor_output_hash": CA_HASH,
            "source_cim_skill_id": "ms.skill.icp_segmentation",
            "source_cim_skill_version": "0.1.0",
            "source_cim_output_hash": ICP_HASH,
        },
        "input_hash": "1111111111111111111111111111111111111111111111111111111111111111",
        "output_hash": "2222222222222222222222222222222222222222222222222222222222222222",
    }
    base.update(overrides)
    return base


def write(name: str, data: dict) -> None:
    path = FIX / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path.name}")


def main() -> None:
    FIX.mkdir(parents=True, exist_ok=True)

    write("input_upstream_refs.json", input_base())

    write(
        "input_invalid_pmc_010.json",
        input_base(
            product_marketing_context=upstream_ref(
                "ms.skill.product_marketing_context", "0.1.0", PMC_HASH
            )
        ),
    )

    bad_hash = input_base()
    del bad_hash["market_research_output"]["source_output_hash"]
    write("input_missing_hash.json", bad_hash)

    bad_cim = input_base()
    del bad_cim["customer_intelligence_reference"]
    write("input_missing_cim.json", bad_cim)

    write(
        "output_proceed.json",
        output_base(),
    )

    write(
        "output_proceed_with_conditions.json",
        output_base(
            verdict="proceed_with_conditions",
            verdict_confidence="medium",
            decision_readiness=readiness("partially_ready"),
            conditions=[condition()],
            recommended_next_stage="positioning",
            executive_summary="Proceed only after budget validation conditions are met.",
        ),
    )

    write(
        "output_revise_segment.json",
        output_base(
            verdict="revise",
            verdict_confidence="medium",
            required_changes=["Narrow segment to mid-market engineering teams"],
            blockers=[
                blocker(
                    "HB-002",
                    category="target_segment",
                    description="Current segment boundaries too broad",
                    remediation_type="material_change",
                    recommended_verdict_effect="revise",
                )
            ],
            recommended_next_stage="additional_research",
            executive_summary="Revise target segment before proceeding.",
        ),
    )

    write(
        "output_revise_pricing.json",
        output_base(
            verdict="revise",
            required_changes=["Adjust pricing model to usage-based tiers"],
            blockers=[
                blocker(
                    "HB-006",
                    category="budget_unavailable",
                    description="Declared pricing exceeds segment budget sensitivity",
                    remediation_type="material_change",
                    recommended_verdict_effect="revise",
                )
            ],
            recommended_next_stage="owner_review",
        ),
    )

    write(
        "output_defer.json",
        output_base(
            verdict="defer",
            verdict_confidence="low",
            defer_reason="Regulatory consultation pending for EU market entry",
            decision_readiness=readiness("partially_ready"),
            blockers=[
                blocker(
                    "HB-003",
                    category="evidence_contradiction",
                    description="External regulatory timing unresolved",
                    remediation_type="timing_or_external",
                    blocking=False,
                    recommended_verdict_effect="defer",
                )
            ],
            recommended_next_stage="owner_review",
        ),
    )

    write(
        "output_stop.json",
        output_base(
            verdict="stop",
            verdict_confidence="high",
            blockers=[
                blocker(
                    "HB-004",
                    category="legal_prohibition",
                    description="Business model prohibited in declared geography",
                    remediation_type="none",
                    recommended_verdict_effect="stop",
                )
            ],
            recommended_next_stage="none",
            executive_summary="Stop pursuit due to legal prohibition.",
        ),
    )

    write(
        "output_insufficient_evidence.json",
        output_base(
            verdict="insufficient_evidence",
            verdict_confidence="unknown",
            decision_readiness=readiness(
                "insufficient_evidence",
                evidence_coverage="minimal",
            ),
            evidence_gaps=["No verified demand signals", "No customer interviews"],
            supporting_evidence=[],
            recommended_next_stage="additional_research",
        ),
    )

    write(
        "output_conflicted_upstream.json",
        output_base(
            verdict="insufficient_evidence",
            verdict_confidence="low",
            decision_readiness=readiness(
                "conflicted",
                unresolved_conflicts=["PMC pricing conflicts with MR pricing signals"],
            ),
            conflicts=[
                {
                    "domain": "pricing",
                    "description": "PMC and MR pricing signals conflict",
                    "conflicting_claims": ["$49/mo", "$99/mo"],
                }
            ],
            decision_dimensions=all_dimensions(
                contradiction_severity={
                    "status": "blocking",
                    "confidence": "low",
                    "contradictory_evidence": ["ev-pricing-conflict"],
                }
            ),
            recommended_next_stage="additional_research",
        ),
    )

    # Invalid semantic fixtures (schema-valid structure but used with semantic validator)
    write(
        "output_invalid_proceed_with_blocker.json",
        output_base(
            verdict="proceed",
            blockers=[
                blocker(
                    "HB-009",
                    category="competitor_disadvantage",
                    description="Unresolvable competitor moat",
                    remediation_type="none",
                    recommended_verdict_effect="stop",
                )
            ],
        ),
    )

    write(
        "output_invalid_stop_no_blocker.json",
        output_base(verdict="stop", blockers=[]),
    )

    write(
        "output_invalid_proceed_empty_evidence.json",
        output_base(verdict="proceed", supporting_evidence=[]),
    )

    write(
        "output_invalid_conditions_empty.json",
        output_base(verdict="proceed_with_conditions", conditions=[]),
    )

    write(
        "output_invalid_revise_no_changes.json",
        output_base(verdict="revise", required_changes=[]),
    )

    write(
        "output_invalid_defer_no_reason.json",
        {k: v for k, v in output_base(verdict="defer").items() if k != "defer_reason"},
    )

    write(
        "output_invalid_insufficient_no_gaps.json",
        output_base(
            verdict="insufficient_evidence",
            evidence_gaps=[],
            decision_readiness=readiness("insufficient_evidence"),
        ),
    )

    write(
        "output_invalid_stop_inference_only.json",
        output_base(
            verdict="stop",
            blockers=[
                blocker(
                    "HB-011",
                    category="unsupported_inference",
                    description="Stop based on unsupported inference",
                    evidence_references=[],
                    remediation_type="none",
                    recommended_verdict_effect="stop",
                )
            ],
            supporting_evidence=[trace("Inference only", trace_type="inference")],
        ),
    )

    write(
        "output_invalid_high_confidence_no_provenance.json",
        output_base(
            verdict="proceed",
            verdict_confidence="high",
            provenance={"skill_id": "ms.skill.market_validation", "skill_version": "0.2.0"},
        ),
    )

    write(
        "cwf_mapping_proceed.json",
        {
            "legacy_biv_value": "proceed",
            "mv_020_value": "proceed",
            "compatibility": "compatible",
            "migration_risk": "low",
            "adapter_required": False,
        },
    )

    write(
        "cwf_mapping_reject_stop.json",
        {
            "legacy_biv_value": "reject",
            "mv_020_value": "stop",
            "compatibility": "requires_adapter",
            "migration_risk": "medium",
            "adapter_required": True,
        },
    )

    write(
        "cwf_mapping_defer_unknown.json",
        {
            "legacy_biv_value": None,
            "mv_020_value": "defer",
            "compatibility": "unknown",
            "migration_risk": "high",
            "adapter_required": True,
            "notes": "No direct BIV equivalent",
        },
    )

    write(
        "positioning_consumer_stub.json",
        {
            "consumer_skill_id": "ms.skill.positioning",
            "consumer_skill_version": "0.2.0",
            "mv_schema_uri": "ms.skill.market_validation/output/0.2.0",
            "mv_version": "0.2.0",
            "mv_output_hash": "2222222222222222222222222222222222222222222222222222222222222222",
            "verdict_consumed": "proceed_with_conditions",
            "selected_segment_ids": ["seg-remote-eng"],
            "conditions_acknowledged": ["cond-budget-validation"],
            "blockers_ignored": [],
            "forbidden_actions": ["reinterpret_stop_as_proceed", "recompute_jtbd"],
        },
    )

    write(
        "offer_consumer_stub.json",
        {
            "consumer_skill_id": "ms.skill.offer_builder",
            "consumer_skill_version": "0.2.0",
            "mv_verdict": "proceed_with_conditions",
            "blocking_conditions_open": ["cond-budget-validation"],
            "blockers_ignored": [],
            "execution_authorized": False,
        },
    )

    parents = [
        {
            "skill_id": "ms.skill.product_marketing_context",
            "version": "0.2.0",
            "hash": PMC_HASH,
        },
        {"skill_id": "ms.skill.market_research", "version": "0.1.0", "hash": MR_HASH},
        {
            "skill_id": "ms.skill.competitor_analysis",
            "version": "0.1.0",
            "hash": CA_HASH,
        },
        {"skill_id": "ms.skill.icp_segmentation", "version": "0.1.0", "hash": ICP_HASH},
    ]
    write(
        "lineage_four_upstream.json",
        {"validation_id": "mv-lineage-001", "parents": parents},
    )


if __name__ == "__main__":
    main()
