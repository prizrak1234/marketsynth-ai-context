"""Deterministic Offer Builder adapter — no external tools."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from app.connectors.evidence import hash_payload
from app.product.offer_builder.contracts import (
    SKILL_ID,
    SKILL_VERSION,
    OfferGenerationContext,
)
from app.product.offer_builder.input_builder import build_skill_input
from app.product.offer_builder.output_validation import compute_output_hash


def _fixture_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "packages"
        / "skills"
        / SKILL_ID
        / "tests"
        / "fixtures"
        / "output_proceed_preferred.json"
    )


def generate_offer_output(context: OfferGenerationContext) -> dict[str, Any]:
    """Produce schema-valid output from governed input + fixture template."""
    skill_input = build_skill_input(context.upstream)
    input_hash = hash_payload(skill_input)

    template = json.loads(_fixture_path().read_text(encoding="utf-8"))
    output = copy.deepcopy(template)

    preferred = output["offer_candidates"][0]
    idea_title = context.launch_objective or "Launch Pack Offer"
    preferred["offer_name"] = idea_title[:120]
    preferred["primary_customer_problem"] = _problem_from_upstream(context)
    preferred["desired_outcome"] = _outcome_from_upstream(context)
    preferred["offer_promise"] = preferred["desired_outcome"]
    preferred["selected_segment_ids"] = list(context.upstream.cim.get("selected_segment_ids", []))
    preferred["positioning_hypothesis_id"] = context.upstream.positioning_hypothesis_id
    preferred["claim_references"] = list(context.upstream.substantiated_claim_ids)

    output["offer_analysis_id"] = str(
        uuid5(NAMESPACE_URL, f"{context.launch_pack_request_id}:{input_hash}")
    )
    output["skill_version"] = SKILL_VERSION
    output["selected_segment_ids"] = list(context.upstream.cim.get("selected_segment_ids", []))
    output["source_cim_reference"] = skill_input["source_cim_reference"]
    output["source_positioning_reference"] = skill_input["source_positioning_reference"]
    output["source_market_validation_reference"] = skill_input[
        "source_market_validation_reference"
    ]
    output["source_claim_substantiation_reference"] = skill_input[
        "source_claim_substantiation_reference"
    ]
    output["source_meaning_reference"] = skill_input.get("source_meaning_reference", {})
    output["inherited_conditions"] = list(context.upstream.inherited_conditions)
    output["inherited_blockers"] = list(context.upstream.inherited_blockers)
    output["human_approval_required"] = True
    output["input_hash"] = input_hash
    output["provenance"] = {
        "generated_by": "offer_builder_runtime",
        "launch_pack_request_id": str(context.launch_pack_request_id),
        "business_verdict_id": str(context.business_verdict_id),
        "adapter": "deterministic",
    }

    if context.upstream.mv_verdict in {"proceed", "proceed_with_conditions"}:
        output["offer_readiness"] = "ready_for_owner_review"
    else:
        output["offer_readiness"] = "exploratory_only"
        output["preferred_offer_id"] = None

    output["output_hash"] = compute_output_hash(output)
    return output


def _problem_from_upstream(context: OfferGenerationContext) -> str:
    payload = context.upstream.market_validation.get("payload", {})
    for cond in payload.get("conditions", []):
        if isinstance(cond, dict) and cond.get("text"):
            return str(cond["text"])[:500]
    return "Customer problem validated during idea research."


def _outcome_from_upstream(context: OfferGenerationContext) -> str:
    payload = context.upstream.positioning.get("payload", {})
    vp = payload.get("value_proposition")
    if vp:
        return str(vp)[:500]
    return "Clear outcome aligned with validated positioning."
