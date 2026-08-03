#!/usr/bin/env python3
"""Scaffold Positioning 0.1.0 fixtures — run once during SKILL-02.7 setup."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "packages" / "skills" / "ms.skill.positioning"
FIX = ROOT / "tests" / "fixtures"

ICP_HASH = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
CIM_HASH = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
CA_HASH = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
MV_HASH = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
MV_PKG_HASH = "ec7c86ce0bc39b5481e336b7749de3cf087d47630be315c639897dd687568f7a"
CIM_URI = (
    "https://schemas.marketsynth.ai/customer-intelligence/0.1.0/"
    "customer-intelligence.schema.json"
)
PROV = {"skill_id": "ms.skill.positioning", "skill_version": "0.1.0"}
RANK_DIMS = {
    "customer_relevance": "high",
    "differentiation_strength": "medium",
    "evidence_strength": "medium",
    "defensibility": "medium",
    "proof_availability": "medium",
    "category_clarity": "high",
    "segment_fit": "high",
    "market_validation_alignment": "high",
    "condition_compatibility": "high",
    "brand_fit": "medium",
    "execution_feasibility": "medium",
    "risk_level": "low",
    "confidence": "medium",
}


def cim_catalog_saas() -> dict:
    return {
        "segment_ids": ["seg-remote-eng"],
        "pain_point_ids": ["pain-seg-remote-eng"],
        "jtbd_ids": ["jtbd-seg-remote-eng"],
        "objection_ids": ["obj-seg-remote-eng"],
        "outcome_ids": ["out-seg-remote-eng"],
        "trigger_ids": ["trg-seg-remote-eng"],
        "barrier_ids": ["bar-seg-remote-eng"],
        "trust_driver_ids": ["trust-seg-remote-eng"],
    }


def cim_catalog_cafe() -> dict:
    return {
        "segment_ids": ["seg-neighborhood-regulars"],
        "pain_point_ids": ["pain-cafe-wait-time"],
        "jtbd_ids": ["jtbd-cafe-community-hub"],
        "objection_ids": ["obj-cafe-price-premium"],
        "outcome_ids": ["out-cafe-third-place"],
        "trigger_ids": ["trg-cafe-local-event"],
        "barrier_ids": ["bar-cafe-parking"],
        "trust_driver_ids": ["trust-cafe-local-sourcing"],
    }


def cim_output_ref(segments: list[str] | None = None, **overrides: object) -> dict:
    base = {
        "source_skill_id": "ms.skill.icp_segmentation",
        "source_skill_version": "0.1.0",
        "source_output_hash": ICP_HASH,
        "cim_schema_uri": CIM_URI,
        "cim_version": "0.1.0",
        "cim_document_hash": CIM_HASH,
        "selected_segment_ids": segments or ["seg-remote-eng"],
        "source_evidence_references": ["ev-seg-seg-remote-eng"],
        "source_unknowns": [
            {"domain": "budget", "description": "Budget bands unverified", "blocking": False}
        ],
        "source_conflicts": [],
    }
    base.update(overrides)
    return base


def cim_input_ref(segments: list[str] | None = None, **overrides: object) -> dict:
    ref = cim_output_ref(segments, **overrides)
    ref["source_status"] = overrides.get("source_status", "ready_for_downstream_use")
    return ref


def upstream(skill_id: str, version: str, out_hash: str, **extra: object) -> dict:
    return {
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


def mv_snapshot(verdict: str, **extra: object) -> dict:
    base = {
        "verdict": verdict,
        "verdict_confidence": extra.get("verdict_confidence", "medium"),
        "conditions": extra.get("conditions", []),
        "blockers": extra.get("blockers", []),
        "required_changes": extra.get("required_changes", []),
        "evidence_gaps": extra.get("evidence_gaps", []),
        "conflicts": extra.get("conflicts", []),
    }
    if extra.get("defer_reason"):
        base["defer_reason"] = extra["defer_reason"]
    return base


def input_base(catalog: dict, segments: list[str], verdict: str, **overrides: object) -> dict:
    base = {
        "customer_intelligence_reference": cim_input_ref(segments),
        "competitor_analysis_output": upstream(
            "ms.skill.competitor_analysis", "0.1.0", CA_HASH
        ),
        "market_validation_output": upstream(
            "ms.skill.market_validation", "0.2.0", MV_HASH
        ),
        "market_validation_snapshot": mv_snapshot(verdict),
        "cim_claim_catalog": catalog,
        "positioning_objectives": ["Develop evidence-backed positioning hypotheses"],
        "selected_segment_ids": segments,
        "product_or_brand_scope": overrides.get("product_or_brand_scope", "B2B async SaaS"),
        "category_assumptions": [],
        "existing_positioning": "",
        "brand_constraints": [],
        "legal_or_compliance_constraints": [],
        "channel_context": ["product-led"],
        "language": "en",
        "required_depth": "standard",
        "provenance": {"submitted_by": "fixture"},
    }
    base.update(overrides)
    return base


def reason_to_believe(statement: str, trace_type: str = "evidence", **extra: object) -> dict:
    item = {"statement": statement, "trace_type": trace_type}
    if trace_type == "evidence":
        item["evidence_references"] = extra.get("evidence_references", ["src-001"])
    return item


def hypothesis(
    hid: str,
    name: str,
    segments: list[str],
    pain_ref: str,
    out_ref: str,
    status: str,
    **extra: object,
) -> dict:
    result = {
        "hypothesis_id": hid,
        "hypothesis_name": name,
        "target_segment_ids": segments,
        "target_customer_summary": extra.get(
            "target_customer_summary", "Remote engineering teams"
        ),
        "market_or_category_frame": extra.get(
            "market_or_category_frame", "Async collaboration for engineering teams"
        ),
        "primary_customer_problem": extra.get(
            "primary_customer_problem", "Meeting overload disrupts deep work"
        ),
        "primary_customer_problem_ref": pain_ref,
        "desired_outcome": extra.get(
            "desired_outcome", "Coordinate without synchronous meetings"
        ),
        "desired_outcome_ref": out_ref,
        "differentiation_basis": extra.get(
            "differentiation_basis",
            "Purpose-built async workflows vs generic project tools",
        ),
        "competitive_alternative": extra.get(
            "competitive_alternative", "Linear, Jira, Slack threads"
        ),
        "value_frame": extra.get(
            "value_frame", "Protect maker time while keeping teams aligned"
        ),
        "reason_to_believe": extra.get(
            "reason_to_believe",
            [
                reason_to_believe(
                    "Competitor gap in async-first UX",
                    evidence_references=["src-001"],
                )
            ],
        ),
        "proof_requirements": extra.get(
            "proof_requirements", ["Case study: reduced meeting hours by 30%"]
        ),
        "key_message": extra.get(
            "key_message", "Async coordination built for engineering teams"
        ),
        "supporting_messages": extra.get(
            "supporting_messages", ["Fewer meetings, clearer ownership"]
        ),
        "exclusion_or_boundary": extra.get(
            "exclusion_or_boundary", "Not for synchronous-heavy sales teams"
        ),
        "evidence_references": extra.get(
            "evidence_references", ["ev-seg-seg-remote-eng", "src-001"]
        ),
        "contradictory_evidence": extra.get("contradictory_evidence", []),
        "assumptions": extra.get("assumptions", []),
        "inferences": extra.get("inferences", []),
        "unknowns": extra.get("unknowns", []),
        "conflicts": extra.get("conflicts", []),
        "validation_conditions": extra.get("validation_conditions", []),
        "risks": extra.get("risks", []),
        "confidence": extra.get("confidence", "medium"),
        "status": status,
        "ranking_dimensions": extra.get("ranking_dimensions", RANK_DIMS),
        "provenance": PROV,
    }
    if extra.get("ranking_tier") is not None:
        result["ranking_tier"] = extra["ranking_tier"]
    if extra.get("ranking_rationale") is not None:
        result["ranking_rationale"] = extra["ranking_rationale"]
    return result


def territory(tid: str, name: str, ttype: str, segments: list[str]) -> dict:
    return {
        "territory_id": tid,
        "territory_name": name,
        "territory_type": ttype,
        "description": f"Territory {name} for positioning exploration",
        "relevant_segment_ids": segments,
        "customer_relevance": "High alignment with declared CIM segment pains",
        "competitive_whitespace": "Competitors emphasize speed over async depth",
        "defensibility": "Workflow depth and integration moat",
        "proof_availability": "Partial — needs customer proof points",
        "market_sophistication_fit": "Solution-aware buyers",
        "evidence_references": ["src-001"],
        "assumptions": [],
        "unknowns": [],
        "risks": [],
        "confidence": "medium",
        "provenance": PROV,
    }


def message_hierarchy(primary: str, **extra: object) -> dict:
    return {
        "primary_message": primary,
        "supporting_messages": extra.get("supporting_messages", ["Reduce meeting load"]),
        "proof_messages": extra.get("proof_messages", ["Engineering teams report fewer standups"]),
        "objection_responses": extra.get(
            "objection_responses",
            [
                {
                    "objection_ref": "obj-seg-remote-eng",
                    "response_framing": "Integrates with existing toolchain",
                    "evidence_references": ["src-001"],
                }
            ],
        ),
        "segment_variants": extra.get(
            "segment_variants",
            [
                {
                    "segment_id": extra.get("segment_id", "seg-remote-eng"),
                    "primary_message_variant": primary,
                    "supporting_messages": ["Built for remote engineering"],
                }
            ],
        ),
        "prohibited_or_unsupported_claims": extra.get(
            "prohibited_or_unsupported_claims", []
        ),
        "evidence_references": extra.get("evidence_references", ["src-001"]),
        "assumptions": [],
        "unknowns": [],
        "provenance": PROV,
    }


def output_provenance() -> dict:
    return {
        "skill_id": "ms.skill.positioning",
        "skill_version": "0.1.0",
        "generated_at": "2026-07-23T00:00:00Z",
        "methodology_ref": "SKILL-02.7",
        "source_cim_skill_id": "ms.skill.icp_segmentation",
        "source_cim_skill_version": "0.1.0",
        "source_cim_output_hash": ICP_HASH,
        "source_cim_document_hash": CIM_HASH,
        "source_competitor_skill_id": "ms.skill.competitor_analysis",
        "source_competitor_skill_version": "0.1.0",
        "source_competitor_output_hash": CA_HASH,
        "source_market_validation_skill_id": "ms.skill.market_validation",
        "source_market_validation_skill_version": "0.2.0",
        "source_market_validation_output_hash": MV_HASH,
    }


def downstream_offer(hypothesis_id: str, segments: list[str], catalog: dict) -> dict:
    return {
        "selected_positioning_hypothesis_id": hypothesis_id,
        "selected_segment_ids": segments,
        "customer_problem": "Meeting overload disrupts deep work",
        "desired_outcome": "Coordinate without synchronous meetings",
        "value_frame": "Protect maker time while keeping teams aligned",
        "differentiation_basis": "Purpose-built async workflows",
        "reason_to_believe": ["Competitor gap in async-first UX"],
        "proof_requirements": ["Case study: reduced meeting hours by 30%"],
        "objections_to_address": catalog.get("objection_ids", [])[:1],
        "buying_triggers": catalog.get("trigger_ids", [])[:1],
        "buying_barriers": catalog.get("barrier_ids", [])[:1],
        "trust_drivers": catalog.get("trust_driver_ids", [])[:1],
        "budget_sensitivity": "Medium — unverified in CIM",
        "conditions": [],
        "blockers": [],
        "evidence_references": ["ev-seg-seg-remote-eng", "src-001"],
        "unknowns": ["Budget bands unverified"],
        "provenance": PROV,
    }


def output_base(
    verdict: str,
    readiness: str,
    hypotheses: list[dict],
    segments: list[str],
    catalog: dict,
    **overrides: object,
) -> dict:
    preferred = overrides.get("preferred_hypothesis_id")
    alternatives = overrides.get(
        "alternative_hypothesis_ids",
        [h["hypothesis_id"] for h in hypotheses if h["hypothesis_id"] != preferred],
    )
    blocked = overrides.get(
        "blocked_hypothesis_ids",
        [h["hypothesis_id"] for h in hypotheses if h["status"] == "blocked"],
    )
    rec = overrides.get("downstream_recommendation", "offer_builder")
    if verdict in {"stop", "defer", "insufficient_evidence"}:
        rec = overrides.get("downstream_recommendation", "blocked")
    base = {
        "positioning_analysis_id": overrides.get("positioning_analysis_id", "pos-001"),
        "skill_id": "ms.skill.positioning",
        "skill_version": "0.1.0",
        "source_cim_reference": cim_output_ref(segments),
        "source_competitor_reference": upstream(
            "ms.skill.competitor_analysis", "0.1.0", CA_HASH
        ),
        "source_market_validation_reference": upstream(
            "ms.skill.market_validation", "0.2.0", MV_HASH
        ),
        "market_validation_verdict_consumed": verdict,
        "selected_segment_ids": segments,
        "positioning_territories": overrides.get(
            "positioning_territories",
            [territory("terr-1", "Async specialist", "niche_specialist", segments)],
        ),
        "positioning_hypotheses": hypotheses,
        "preferred_hypothesis_id": preferred,
        "alternative_hypothesis_ids": alternatives,
        "blocked_hypothesis_ids": blocked,
        "message_hierarchy": overrides.get(
            "message_hierarchy",
            message_hierarchy("Async coordination built for engineering teams"),
        ),
        "differentiation_summary": overrides.get(
            "differentiation_summary",
            "Competitors optimize speed; whitespace in async-first depth",
        ),
        "reason_to_believe_requirements": ["Customer proof of meeting reduction"],
        "proof_gaps": overrides.get("proof_gaps", []),
        "unsupported_claims": overrides.get("unsupported_claims", []),
        "conditions_inherited": overrides.get("conditions_inherited", []),
        "blockers_inherited": overrides.get("blockers_inherited", []),
        "positioning_risks": overrides.get("positioning_risks", []),
        "assumptions": [],
        "inferences": [],
        "unknowns": overrides.get("unknowns", []),
        "conflicts": overrides.get("conflicts", []),
        "evidence_gaps": overrides.get("evidence_gaps", []),
        "coverage": overrides.get("coverage", "partial"),
        "evidence_quality": overrides.get("evidence_quality", "partial"),
        "research_status": overrides.get("research_status", "partially_complete"),
        "positioning_readiness": readiness,
        "downstream_offer_inputs": overrides.get("downstream_offer_inputs", []),
        "downstream_recommendation": rec,
        "human_approval_required": True,
        "provenance": output_provenance(),
        "input_hash": "1111111111111111111111111111111111111111111111111111111111111111",
        "output_hash": "2222222222222222222222222222222222222222222222222222222222222222",
    }
    base.update({k: v for k, v in overrides.items() if k.startswith("_") is False})
    if base.get("preferred_hypothesis_id") is None:
        base.pop("preferred_hypothesis_id", None)
    return base


def write(name: str, data: dict) -> None:
    path = FIX / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {name}")


def main() -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    cat = cim_catalog_saas()
    segs = ["seg-remote-eng"]

    write("input_upstream_refs.json", input_base(cat, segs, "proceed"))

    h1 = hypothesis(
        "pos-h1",
        "Async-first engineering hub",
        segs,
        "pain-seg-remote-eng",
        "out-seg-remote-eng",
        "recommended",
        ranking_tier="preferred",
        ranking_rationale="Strongest segment-problem fit with competitor whitespace",
    )
    h2 = hypothesis(
        "pos-h2",
        "Meeting replacement layer",
        segs,
        "pain-seg-remote-eng",
        "out-seg-remote-eng",
        "viable_alternative",
        differentiation_basis="Replace standups with structured async updates",
        ranking_tier="alternative",
    )
    h3 = hypothesis(
        "pos-h3",
        "Generic project tracker",
        segs,
        "pain-seg-remote-eng",
        "out-seg-remote-eng",
        "rejected",
        differentiation_basis="Competes head-on with entrenched tools",
        ranking_tier="blocked",
    )
    write(
        "output_saas_three_hypotheses.json",
        output_base(
            "proceed",
            "ready_for_offer_design",
            [h1, h2, h3],
            segs,
            cat,
            preferred_hypothesis_id="pos-h1",
            alternative_hypothesis_ids=["pos-h2"],
            blocked_hypothesis_ids=[],
            downstream_offer_inputs=[downstream_offer("pos-h1", segs, cat)],
        ),
    )

    cafe_cat = cim_catalog_cafe()
    cafe_segs = ["seg-neighborhood-regulars"]
    ch1 = hypothesis(
        "pos-cafe-1",
        "Third-place community café",
        cafe_segs,
        "pain-cafe-wait-time",
        "out-cafe-third-place",
        "viable_alternative",
        target_customer_summary="Neighborhood regulars seeking community",
        market_or_category_frame="Local specialty café",
        primary_customer_problem="Long waits during peak hours",
        desired_outcome="Reliable third-place experience",
        competitive_alternative="Chain coffee shops",
        value_frame="Community hub with consistent quality",
        key_message="Your neighborhood third place",
        evidence_references=["ev-cafe-001", "src-cafe-001"],
        reason_to_believe=[
            reason_to_believe(
                "Competitors lack community programming",
                evidence_references=["src-cafe-001"],
            )
        ],
    )
    write(
        "output_cafe_alternatives.json",
        output_base(
            "proceed",
            "partially_ready",
            [ch1],
            cafe_segs,
            cafe_cat,
            positioning_analysis_id="pos-cafe-001",
            preferred_hypothesis_id=None,
            alternative_hypothesis_ids=["pos-cafe-1"],
            blocked_hypothesis_ids=[],
            message_hierarchy=message_hierarchy(
                "Your neighborhood third place",
                segment_id="seg-neighborhood-regulars",
            ),
        ),
    )

    write(
        "output_proceed_preferred.json",
        output_base(
            "proceed",
            "ready_for_offer_design",
            [h1],
            segs,
            cat,
            positioning_analysis_id="pos-proceed-001",
            preferred_hypothesis_id="pos-h1",
            alternative_hypothesis_ids=[],
            downstream_offer_inputs=[downstream_offer("pos-h1", segs, cat)],
        ),
    )

    cond = [
        {
            "condition_id": "cond-budget-validation",
            "statement": "Validate budget bands for target segment",
            "source_reference": "cond-budget-validation",
        }
    ]
    write(
        "output_proceed_with_conditions.json",
        output_base(
            "proceed_with_conditions",
            "partially_ready",
            [h1, h2],
            segs,
            cat,
            preferred_hypothesis_id="pos-h1",
            conditions_inherited=cond,
            downstream_offer_inputs=[
                {
                    **downstream_offer("pos-h1", segs, cat),
                    "conditions": ["Validate budget bands for target segment"],
                }
            ],
        ),
    )

    write(
        "output_revise.json",
        output_base(
            "revise",
            "partially_ready",
            [
                hypothesis(
                    "pos-revise-1",
                    "Revised async positioning",
                    segs,
                    "pain-seg-remote-eng",
                    "out-seg-remote-eng",
                    "exploratory",
                    validation_conditions=[
                        "Address MV required change: narrow ICP to 50+ eng teams"
                    ],
                )
            ],
            segs,
            cat,
            preferred_hypothesis_id=None,
            downstream_recommendation="owner_review",
            evidence_gaps=["ICP scope revision pending"],
        ),
    )

    write(
        "output_defer.json",
        output_base(
            "defer",
            "exploratory_only",
            [
                hypothesis(
                    "pos-defer-1",
                    "Exploratory async frame",
                    segs,
                    "pain-seg-remote-eng",
                    "out-seg-remote-eng",
                    "exploratory",
                    confidence="low",
                )
            ],
            segs,
            cat,
            preferred_hypothesis_id=None,
            downstream_recommendation="blocked",
            evidence_gaps=["Seasonal demand unverified"],
        ),
    )

    write(
        "output_stop.json",
        output_base(
            "stop",
            "blocked",
            [
                hypothesis(
                    "pos-stop-1",
                    "Diagnostic — blocked market",
                    segs,
                    "pain-seg-remote-eng",
                    "out-seg-remote-eng",
                    "blocked",
                    confidence="low",
                    ranking_tier="blocked",
                    key_message="Hypothetical only — market blocked",
                )
            ],
            segs,
            cat,
            preferred_hypothesis_id=None,
            blockers_inherited=[
                {
                    "blocker_id": "blk-market-saturation",
                    "description": "Market saturation blocker from MV",
                    "blocking": True,
                    "source_reference": "blk-market-saturation",
                }
            ],
            downstream_recommendation="blocked",
            research_status="out_of_scope",
        ),
    )

    write(
        "output_insufficient_evidence.json",
        output_base(
            "insufficient_evidence",
            "insufficient_evidence",
            [
                hypothesis(
                    "pos-ie-1",
                    "Low-evidence exploratory frame",
                    segs,
                    "pain-seg-remote-eng",
                    "out-seg-remote-eng",
                    "insufficient_evidence",
                    confidence="low",
                    evidence_references=["ev-seg-seg-remote-eng"],
                )
            ],
            segs,
            cat,
            preferred_hypothesis_id=None,
            downstream_recommendation="additional_research",
            evidence_gaps=["Competitor pricing unverified"],
            evidence_quality="insufficient",
        ),
    )

    write(
        "output_conflicted_competitor.json",
        output_base(
            "proceed",
            "conflicted",
            [h1],
            segs,
            cat,
            preferred_hypothesis_id=None,
            conflicts=[
                {
                    "conflict_id": "conf-comp-pricing",
                    "description": "Conflicting competitor pricing signals",
                    "severity": "major",
                    "evidence_references": ["src-001", "src-002"],
                }
            ],
            evidence_quality="conflicted",
            research_status="conflicted",
        ),
    )

    bad_cim = input_base(cat, segs, "proceed")
    bad_cim["customer_intelligence_reference"] = cim_input_ref(segs, cim_document_hash="")
    write("input_missing_cim_hash.json", bad_cim)

    bad_seg = input_base(cat, ["seg-unknown"], "proceed")
    write("input_unknown_segment_id.json", bad_seg)

    bad_pain = output_base(
        "proceed",
        "ready_for_offer_design",
        [
            hypothesis(
                "pos-bad-pain",
                "Invented pain",
                segs,
                "pain-invented-not-in-cim",
                "out-seg-remote-eng",
                "recommended",
            )
        ],
        segs,
        cat,
        preferred_hypothesis_id="pos-bad-pain",
    )
    write("output_unsupported_pain.json", bad_pain)

    bad_pref = output_base(
        "proceed",
        "ready_for_offer_design",
        [
            hypothesis(
                "pos-no-ev",
                "No evidence preferred",
                segs,
                "pain-seg-remote-eng",
                "out-seg-remote-eng",
                "recommended",
                evidence_references=[],
            )
        ],
        segs,
        cat,
        preferred_hypothesis_id="pos-no-ev",
    )
    write("output_preferred_without_evidence.json", bad_pref)

    bad_claim = output_base(
        "proceed",
        "ready_for_offer_design",
        [
            hypothesis(
                "pos-bad-claim",
                "Unsupported key message",
                segs,
                "pain-seg-remote-eng",
                "out-seg-remote-eng",
                "recommended",
                key_message="Guaranteed 10x productivity — unverified",
            )
        ],
        segs,
        cat,
        preferred_hypothesis_id="pos-bad-claim",
        unsupported_claims=["Guaranteed 10x productivity — unverified"],
    )
    write("output_unsupported_claim_key_message.json", bad_claim)

    bad_ready = output_base(
        "stop",
        "ready_for_offer_design",
        [
            hypothesis(
                "pos-stop-rec",
                "Should not be recommended",
                segs,
                "pain-seg-remote-eng",
                "out-seg-remote-eng",
                "recommended",
            )
        ],
        segs,
        cat,
        preferred_hypothesis_id="pos-stop-rec",
    )
    write("output_ready_despite_stop.json", bad_ready)

    bad_conf = output_base(
        "insufficient_evidence",
        "exploratory_only",
        [
            hypothesis(
                "pos-high-conf",
                "High confidence invalid",
                segs,
                "pain-seg-remote-eng",
                "out-seg-remote-eng",
                "exploratory",
                confidence="high",
            )
        ],
        segs,
        cat,
        preferred_hypothesis_id=None,
    )
    write("output_high_confidence_insufficient_evidence.json", bad_conf)

    bad_offer = output_base(
        "proceed",
        "ready_for_offer_design",
        [h1],
        segs,
        cat,
        preferred_hypothesis_id="pos-h1",
    )
    bad_offer["final_offer"] = {"package_name": "Pro", "price": 99}
    write("output_offer_field_injected.json", bad_offer)

    write(
        "consumer_offer_builder_stub.json",
        {
            "consumer_skill_id": "ms.skill.offer_builder",
            "selected_hypothesis_id": "pos-h1",
            "selected_segment_ids": segs,
            "message_hierarchy_ref": "message_hierarchy",
            "proof_requirements": ["Case study: reduced meeting hours by 30%"],
            "conditions_inherited": [],
            "blockers_inherited": [],
            "execution_authorized": False,
            "verdict_override_attempted": False,
        },
    )

    write(
        "consumer_content_strategy_stub.json",
        {
            "consumer_skill_id": "ms.skill.content_strategy",
            "selected_hypothesis_id": "pos-h1",
            "selected_segment_ids": segs,
            "message_hierarchy_ref": "message_hierarchy",
            "proof_requirements": ["Case study: reduced meeting hours by 30%"],
            "conditions_inherited": [],
            "blockers_inherited": [],
            "execution_authorized": False,
        },
    )

    write(
        "lineage_cim_ca_mv_parents.json",
        {
            "child_skill_id": "ms.skill.positioning",
            "child_skill_version": "0.1.0",
            "child_output_hash": "2222222222222222222222222222222222222222222222222222222222222222",
            "parents": [
                {
                    "skill_id": "ms.skill.icp_segmentation",
                    "skill_version": "0.1.0",
                    "output_hash": ICP_HASH,
                    "cim_document_hash": CIM_HASH,
                },
                {
                    "skill_id": "ms.skill.competitor_analysis",
                    "skill_version": "0.1.0",
                    "output_hash": CA_HASH,
                },
                {
                    "skill_id": "ms.skill.market_validation",
                    "skill_version": "0.2.0",
                    "output_hash": MV_HASH,
                    "package_hash": MV_PKG_HASH,
                },
            ],
        },
    )


if __name__ == "__main__":
    main()
