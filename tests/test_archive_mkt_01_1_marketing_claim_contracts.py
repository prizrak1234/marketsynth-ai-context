"""ARCHIVE-MKT-01.1 — Marketing claims shared schema contract tests."""

from __future__ import annotations

import pytest
from jsonschema.exceptions import ValidationError
from tests.support.marketing_claims_validation import (
    CANONICAL_URI_BASE,
    FROZEN_BUNDLE_HASH,
    load_freeze_manifest,
    recompute_bundle_hash,
    validate_marketing_claim,
    validate_marketing_claim_semantics,
    validate_promise_candidate,
    validate_promise_semantics,
    validate_risk_reversal,
    validate_risk_reversal_semantics,
)
from tests.support.marketing_claims_validation import bundle_has_remote_refs

PROV = {"source_type": "fixture", "source_id": "test-001"}


def _base_claim(**overrides: object) -> dict:
    claim = {
        "claim_id": "claim-1",
        "claim_type": "customer_benefit",
        "statement": "Teams may reduce meeting load with async workflows",
        "target_segment_ids": ["seg-remote-eng"],
        "evidence_references": ["ev-001"],
        "proof_requirements": ["pr-001"],
        "assumptions": [],
        "inferences": [],
        "limitations": [],
        "conditions": [],
        "verification_status": "partially_verified",
        "substantiation_status": "partially_supported",
        "risk_level": "medium",
        "human_review_required": True,
        "legal_review_required": False,
        "prohibited": False,
        "provenance": PROV,
    }
    claim.update(overrides)
    return claim


def test_01_bundle_exists_and_hash_deterministic() -> None:
    manifest = load_freeze_manifest()
    assert manifest["bundle_hash"] == FROZEN_BUNDLE_HASH
    recomputed = recompute_bundle_hash()
    assert recomputed == FROZEN_BUNDLE_HASH


def test_02_canonical_uri_base() -> None:
    manifest = load_freeze_manifest()
    assert manifest["canonical_uri_base"] == CANONICAL_URI_BASE


def test_03_verified_claim_without_evidence_rejected_semantically() -> None:
    claim = _base_claim(verification_status="verified", evidence_references=[])
    errors = validate_marketing_claim_semantics(claim)
    assert any("verified claim without evidence" in e for e in errors)


def test_04_financial_claim_requires_review() -> None:
    claim = _base_claim(
        claim_type="income_or_financial",
        statement="Earn more with our program",
        legal_review_required=False,
        human_review_required=False,
    )
    errors = validate_marketing_claim_semantics(claim)
    assert any("financial" in e for e in errors)


def test_05_guaranteed_income_prohibited() -> None:
    claim = _base_claim(
        claim_type="income_or_financial",
        statement="100% guaranteed income within 30 days",
        prohibited=False,
        legal_review_required=True,
        human_review_required=True,
    )
    errors = validate_marketing_claim_semantics(claim)
    assert any("prohibited pattern" in e for e in errors)


def test_06_hundred_percent_safety_prohibited() -> None:
    claim = _base_claim(
        claim_type="safety",
        statement="100% safety — zero risk for all users",
        prohibited=False,
    )
    errors = validate_marketing_claim_semantics(claim)
    assert len(errors) >= 1


def test_07_statistical_claim_without_source_rejected() -> None:
    claim = _base_claim(
        claim_type="statistical",
        statement="90% of users improve outcomes",
        evidence_references=[],
    )
    errors = validate_marketing_claim_semantics(claim)
    assert any("statistical claim without source" in e for e in errors)


def test_08_comparative_claim_without_basis_rejected() -> None:
    claim = _base_claim(
        claim_type="comparative",
        statement="Better than all competitors",
        conditions=[],
    )
    errors = validate_marketing_claim_semantics(claim)
    assert any("comparative claim without comparison basis" in e for e in errors)


def test_09_assumption_cannot_become_verified() -> None:
    claim = _base_claim(
        verification_status="verified",
        assumptions=["Customer wants faster results"],
        evidence_references=["ev-001"],
    )
    errors = validate_marketing_claim_semantics(claim)
    assert any("assumption cannot become verified" in e for e in errors)


def test_10_risk_reversal_does_not_imply_guaranteed_result() -> None:
    rr = {
        "risk_reversal_id": "rr-1",
        "reversal_type": "refund",
        "description": "30-day refund",
        "reduces_commercial_risk": True,
        "proves_outcome": True,
        "conditions": [],
        "limitations": [],
        "evidence_references": [],
        "provenance": PROV,
    }
    with pytest.raises(ValidationError):
        validate_risk_reversal(rr)
    errors = validate_risk_reversal_semantics({**rr, "proves_outcome": True})
    assert any("does not imply" in e for e in errors)


def test_11_valid_risk_reversal_proves_outcome_false() -> None:
    rr = {
        "risk_reversal_id": "rr-1",
        "reversal_type": "refund",
        "description": "30-day refund if onboarding incomplete",
        "reduces_commercial_risk": True,
        "proves_outcome": False,
        "conditions": [],
        "limitations": [],
        "evidence_references": [],
        "provenance": PROV,
    }
    validate_risk_reversal(rr)
    assert not validate_risk_reversal_semantics(rr)


def test_12_unsupported_promise_not_customer_facing() -> None:
    promise = {
        "promise_id": "p-1",
        "desired_outcome_reference": "out-1",
        "target_segment_ids": ["seg-remote-eng"],
        "proposed_statement": "Guaranteed transformation",
        "evidence_references": [],
        "proof_requirements": [],
        "conditions": [],
        "limitations": [],
        "risks": [],
        "substantiation_status": "unsupported",
        "confidence": "low",
        "prohibited": False,
        "human_review_required": True,
        "provenance": PROV,
        "customer_facing": True,
    }
    errors = validate_promise_semantics(promise)
    assert any("unsupported promise cannot be customer-facing" in e for e in errors)


def test_13_no_remote_refs_in_bundle() -> None:
    assert bundle_has_remote_refs() == []


def test_14_marketing_claim_schema_validates() -> None:
    validate_marketing_claim(_base_claim())


def test_15_promise_candidate_schema_validates() -> None:
    promise = {
        "promise_id": "p-1",
        "desired_outcome_reference": "out-1",
        "target_segment_ids": ["seg-remote-eng"],
        "proposed_statement": "Reduce meeting load for adopting teams",
        "evidence_references": ["ev-001"],
        "proof_requirements": [],
        "conditions": [],
        "limitations": [],
        "risks": [],
        "substantiation_status": "partially_supported",
        "confidence": "medium",
        "prohibited": False,
        "human_review_required": True,
        "provenance": PROV,
    }
    validate_promise_candidate(promise)


def test_16_bundle_schemas_count() -> None:
    manifest = load_freeze_manifest()
    assert len(manifest["file_hashes"]) == 9
