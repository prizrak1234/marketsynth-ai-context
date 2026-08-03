#!/usr/bin/env python3
# ruff: noqa: E501
"""Scaffold ARCHIVE-MKT-01 marketing claims bundle and skill packages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAIMS_ROOT = REPO / "packages" / "knowledge" / "marketing_claims" / "0.1.0"

ORDINAL = {"type": "string", "enum": ["high", "medium", "low", "unknown"]}
PROV = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "source_type": {"type": "string", "maxLength": 64},
        "source_id": {"type": "string", "maxLength": 128},
        "generated_at": {"type": "string", "maxLength": 64},
        "methodology_ref": {"type": "string", "maxLength": 256},
    },
    "required": ["source_type"],
}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def schema(id_suffix: str, title: str, props: dict, required: list[str]) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://schemas.marketsynth.ai/marketing-claims/0.1.0/{id_suffix}",
        "title": title,
        "type": "object",
        "additionalProperties": False,
        "properties": props,
        "required": required,
    }


def build_claims_schemas() -> None:
    write_json(
        CLAIMS_ROOT / "provenance.schema.json",
        schema(
            "provenance.schema.json",
            "MarketingClaimProvenance",
            {
                "source_type": {"type": "string", "maxLength": 64},
                "source_id": {"type": "string", "maxLength": 128},
                "skill_id": {"type": "string", "maxLength": 128},
                "skill_version": {"type": "string", "maxLength": 32},
                "generated_at": {"type": "string", "maxLength": 64},
            },
            ["source_type"],
        ),
    )
    write_json(
        CLAIMS_ROOT / "marketing-claim.schema.json",
        schema(
            "marketing-claim.schema.json",
            "MarketingClaim",
            {
                "claim_id": {"type": "string", "maxLength": 128},
                "claim_type": {
                    "type": "string",
                    "enum": [
                        "product_capability",
                        "customer_benefit",
                        "outcome",
                        "time_to_value",
                        "comparative",
                        "pricing",
                        "savings",
                        "income_or_financial",
                        "safety",
                        "performance",
                        "service",
                        "convenience",
                        "availability",
                        "guarantee",
                        "testimonial",
                        "statistical",
                        "unknown",
                    ],
                },
                "statement": {"type": "string", "maxLength": 4000},
                "target_segment_ids": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 128},
                },
                "product_capability_reference": {"type": "string", "maxLength": 128},
                "customer_need_reference": {"type": "string", "maxLength": 128},
                "evidence_references": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 256},
                },
                "proof_requirements": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 256},
                },
                "assumptions": {"type": "array", "items": {"type": "string", "maxLength": 2000}},
                "inferences": {"type": "array", "items": {"type": "string", "maxLength": 2000}},
                "limitations": {"type": "array", "items": {"type": "string", "maxLength": 2000}},
                "conditions": {"type": "array", "items": {"type": "string", "maxLength": 2000}},
                "jurisdiction_context": {"type": "string", "maxLength": 500},
                "regulated_domain": {"type": "string", "maxLength": 128},
                "verification_status": {
                    "type": "string",
                    "enum": ["unverified", "partially_verified", "verified", "contradicted", "unknown"],
                },
                "substantiation_status": {
                    "type": "string",
                    "enum": [
                        "unsupported",
                        "partially_supported",
                        "supported",
                        "support_conflicted",
                        "prohibited",
                        "requires_review",
                    ],
                },
                "risk_level": ORDINAL,
                "human_review_required": {"type": "boolean"},
                "legal_review_required": {"type": "boolean"},
                "prohibited": {"type": "boolean"},
                "prohibition_reason": {"type": "string", "maxLength": 2000},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            [
                "claim_id",
                "claim_type",
                "statement",
                "target_segment_ids",
                "evidence_references",
                "proof_requirements",
                "assumptions",
                "inferences",
                "limitations",
                "conditions",
                "verification_status",
                "substantiation_status",
                "risk_level",
                "human_review_required",
                "legal_review_required",
                "prohibited",
                "provenance",
            ],
        ),
    )
    # Additional schemas abbreviated for brevity - write promise, proof, etc.
    for name, title, props, req in [
        (
            "promise-candidate.schema.json",
            "PromiseCandidate",
            {
                "promise_id": {"type": "string", "maxLength": 128},
                "desired_outcome_reference": {"type": "string", "maxLength": 128},
                "target_segment_ids": {"type": "array", "items": {"type": "string"}},
                "proposed_statement": {"type": "string", "maxLength": 4000},
                "delivery_mechanism_reference": {"type": "string", "maxLength": 128},
                "time_horizon": {"type": "string", "maxLength": 500},
                "customer_effort": {"type": "string", "maxLength": 2000},
                "provider_responsibility": {"type": "string", "maxLength": 2000},
                "customer_responsibility": {"type": "string", "maxLength": 2000},
                "evidence_references": {"type": "array", "items": {"type": "string"}},
                "proof_requirements": {"type": "array", "items": {"type": "string"}},
                "conditions": {"type": "array", "items": {"type": "string"}},
                "limitations": {"type": "array", "items": {"type": "string"}},
                "risks": {"type": "array", "items": {"type": "string"}},
                "substantiation_status": {
                    "type": "string",
                    "enum": [
                        "unsupported",
                        "partially_supported",
                        "supported",
                        "support_conflicted",
                        "prohibited",
                        "requires_review",
                    ],
                },
                "confidence": ORDINAL,
                "prohibited": {"type": "boolean"},
                "human_review_required": {"type": "boolean"},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            [
                "promise_id",
                "desired_outcome_reference",
                "target_segment_ids",
                "proposed_statement",
                "evidence_references",
                "proof_requirements",
                "conditions",
                "limitations",
                "risks",
                "substantiation_status",
                "confidence",
                "prohibited",
                "human_review_required",
                "provenance",
            ],
        ),
        (
            "proof-requirement.schema.json",
            "ProofRequirement",
            {
                "proof_requirement_id": {"type": "string", "maxLength": 128},
                "claim_reference": {"type": "string", "maxLength": 128},
                "proof_type": {
                    "type": "string",
                    "enum": [
                        "product_capability_evidence",
                        "process_demonstration",
                        "customer_case",
                        "testimonial",
                        "controlled_test",
                        "pilot",
                        "statistical_source",
                        "independent_source",
                        "certification",
                        "warranty",
                        "refund_policy",
                        "success_fee",
                        "service_level",
                        "transparent_limitation",
                        "unknown",
                    ],
                },
                "description": {"type": "string", "maxLength": 4000},
                "evidence_references": {"type": "array", "items": {"type": "string"}},
                "status": {
                    "type": "string",
                    "enum": ["open", "partially_met", "met", "unmet", "unknown"],
                },
                "provenance": {"$ref": "provenance.schema.json"},
            },
            [
                "proof_requirement_id",
                "claim_reference",
                "proof_type",
                "description",
                "evidence_references",
                "status",
                "provenance",
            ],
        ),
        (
            "claim-evidence-link.schema.json",
            "ClaimEvidenceLink",
            {
                "link_id": {"type": "string", "maxLength": 128},
                "claim_id": {"type": "string", "maxLength": 128},
                "evidence_reference": {"type": "string", "maxLength": 256},
                "evidence_class": {"type": "string", "maxLength": 64},
                "supports": {"type": "boolean"},
                "contradicts": {"type": "boolean"},
                "notes": {"type": "string", "maxLength": 2000},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            ["link_id", "claim_id", "evidence_reference", "evidence_class", "supports", "provenance"],
        ),
        (
            "risk-reversal.schema.json",
            "RiskReversal",
            {
                "risk_reversal_id": {"type": "string", "maxLength": 128},
                "reversal_type": {
                    "type": "string",
                    "enum": [
                        "refund",
                        "trial",
                        "pilot",
                        "phased_payment",
                        "success_fee",
                        "milestone_payment",
                        "cancellation_right",
                        "limited_guarantee",
                        "warranty",
                        "service_credit",
                        "proof_before_purchase",
                        "no_risk_reversal",
                        "unknown",
                    ],
                },
                "description": {"type": "string", "maxLength": 4000},
                "reduces_commercial_risk": {"type": "boolean"},
                "proves_outcome": {"type": "boolean", "const": False},
                "conditions": {"type": "array", "items": {"type": "string"}},
                "limitations": {"type": "array", "items": {"type": "string"}},
                "evidence_references": {"type": "array", "items": {"type": "string"}},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            [
                "risk_reversal_id",
                "reversal_type",
                "description",
                "reduces_commercial_risk",
                "proves_outcome",
                "conditions",
                "limitations",
                "evidence_references",
                "provenance",
            ],
        ),
        (
            "guarantee-proposal.schema.json",
            "GuaranteeProposal",
            {
                "guarantee_id": {"type": "string", "maxLength": 128},
                "guarantee_type": {"type": "string", "maxLength": 128},
                "statement": {"type": "string", "maxLength": 4000},
                "scope": {"type": "string", "maxLength": 2000},
                "conditions": {"type": "array", "items": {"type": "string"}},
                "legal_review_required": {"type": "boolean"},
                "outcome_guarantee": {"type": "boolean"},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            [
                "guarantee_id",
                "guarantee_type",
                "statement",
                "scope",
                "conditions",
                "legal_review_required",
                "outcome_guarantee",
                "provenance",
            ],
        ),
        (
            "price-justification.schema.json",
            "PriceJustification",
            {
                "justification_id": {"type": "string", "maxLength": 128},
                "justification_type": {
                    "type": "string",
                    "enum": [
                        "lower_total_cost",
                        "faster_outcome",
                        "earning_potential",
                        "premium_experience",
                        "comfort",
                        "duration",
                        "location_access",
                        "additional_components",
                        "bundle",
                        "upsell",
                        "cross_sell",
                        "unknown",
                    ],
                },
                "statement": {"type": "string", "maxLength": 4000},
                "comparison_basis": {"type": "string", "maxLength": 2000},
                "is_assumption": {"type": "boolean"},
                "evidence_references": {"type": "array", "items": {"type": "string"}},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            [
                "justification_id",
                "justification_type",
                "statement",
                "comparison_basis",
                "is_assumption",
                "evidence_references",
                "provenance",
            ],
        ),
        (
            "claim-compliance-finding.schema.json",
            "ClaimComplianceFinding",
            {
                "finding_id": {"type": "string", "maxLength": 128},
                "claim_id": {"type": "string", "maxLength": 128},
                "severity": {
                    "type": "string",
                    "enum": ["critical", "major", "minor", "informational", "unknown"],
                },
                "finding_type": {"type": "string", "maxLength": 128},
                "description": {"type": "string", "maxLength": 4000},
                "required_action": {"type": "string", "maxLength": 2000},
                "legal_review_required": {"type": "boolean"},
                "provenance": {"$ref": "provenance.schema.json"},
            },
            [
                "finding_id",
                "claim_id",
                "severity",
                "finding_type",
                "description",
                "required_action",
                "legal_review_required",
                "provenance",
            ],
        ),
    ]:
        write_json(CLAIMS_ROOT / name, schema(name, title, props, req))

    # freeze manifest
    files = sorted(p.name for p in CLAIMS_ROOT.glob("*.schema.json"))
    file_hashes = {}
    for name in files:
        content = (CLAIMS_ROOT / name).read_bytes()
        file_hashes[name] = hashlib.sha256(content).hexdigest()
    bundle_hash = hashlib.sha256(
        json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    write_json(
        CLAIMS_ROOT / "freeze_manifest.json",
        {
            "schema_version": "0.1.0",
            "canonical_uri_base": "https://schemas.marketsynth.ai/marketing-claims/0.1.0/",
            "schema_status": "frozen",
            "file_hashes": file_hashes,
            "bundle_hash": bundle_hash,
            "generated_at": "2026-07-23T00:00:00Z",
        },
    )
    print(f"Claims bundle hash: {bundle_hash}")


if __name__ == "__main__":
    build_claims_schemas()
