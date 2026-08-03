"""ARCHIVE-MKT-01.6 — Integrated foundation invariant tests."""

from __future__ import annotations

from pathlib import Path

from app.skills.hashing import calculate_skill_package_hash
from app.skills.legacy_output_contract import expected_frozen_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from tests.support.archive_mkt_validation import (
    CIM_BUNDLE_HASH,
    MV_020_PKG_HASH,
    PACKAGE_HASHES,
    POS_PKG_HASH,
    load_json_fixture,
    validate_interview_output_semantics,
    validate_meaning_output_semantics,
    validate_offer_output_semantics,
    validate_substantiation_semantics,
)
from tests.support.marketing_claims_validation import FROZEN_BUNDLE_HASH, load_freeze_manifest

REPO = Path(__file__).resolve().parents[1]
AUDIT_DOC = REPO / "docs/rfc/ARCHIVE-MKT-01-INTEGRATED-FREEZE-AUDIT.md"

ARCHIVE_SKILLS = (
    "ms.skill.customer_interview_design",
    "ms.skill.customer_meaning_extraction",
    "ms.skill.claim_substantiation",
    "ms.skill.offer_builder",
)


def test_01_audit_document_exists() -> None:
    assert AUDIT_DOC.is_file()


def test_02_cim_bundle_hash_unchanged() -> None:
    assert CIM_BUNDLE_HASH == "b13cc76eb8f6405d114a457a8a4bf12a4a5330d9a37bd0adcfd93f48353421ea"


def test_03_frozen_positioning_and_mv_unchanged() -> None:
    assert expected_frozen_package_hash("ms.skill.positioning", "0.1.0") == POS_PKG_HASH
    assert expected_frozen_package_hash("ms.skill.market_validation", "0.2.0") == MV_020_PKG_HASH


def test_04_marketing_claims_bundle_frozen() -> None:
    assert load_freeze_manifest()["bundle_hash"] == FROZEN_BUNDLE_HASH


def test_05_all_archive_skills_validate() -> None:
    for skill_id in ARCHIVE_SKILLS:
        root = REPO / "packages" / "skills" / skill_id
        assert validate_skill_package(root).valid is True


def test_06_all_archive_skills_candidate_non_production() -> None:
    for skill_id in ARCHIVE_SKILLS:
        root = REPO / "packages" / "skills" / skill_id
        projection = project_validation_report(validate_skill_package(root))
        assert derive_eligibility_view(projection.version_record).production_eligible is False


def test_07_deterministic_archive_package_hashes() -> None:
    for skill_id, expected in PACKAGE_HASHES.items():
        root = REPO / "packages" / "skills" / skill_id
        assert calculate_skill_package_hash(root) == expected


def test_08_interview_questions_not_evidence() -> None:
    data = load_json_fixture(
        "ms.skill.customer_interview_design",
        "tests/fixtures/output_valid_guide.json",
    )
    for q in data["questions"]:
        assert q.get("expected_evidence_type") == "user_statement"


def test_09_substantiation_before_offer_claims() -> None:
    cs = load_json_fixture(
        "ms.skill.claim_substantiation",
        "tests/fixtures/output_valid_substantiation.json",
    )
    ob = load_json_fixture(
        "ms.skill.offer_builder",
        "tests/fixtures/output_proceed_preferred.json",
    )
    allowed = {c["claim_id"] for c in cs["offer_builder_claim_inputs"]}
    for offer in ob["offer_candidates"]:
        if offer.get("status") == "preferred":
            assert set(offer["claim_references"]).issubset(allowed)


def test_10_prohibited_claims_excluded_from_offer() -> None:
    ob = load_json_fixture(
        "ms.skill.offer_builder",
        "tests/fixtures/output_proceed_preferred.json",
    )
    assert "claim-income-bad" in ob["unsupported_claims_excluded"]


def test_11_contour_semantic_chain_clean() -> None:
    interview = load_json_fixture(
        "ms.skill.customer_interview_design",
        "tests/fixtures/output_valid_guide.json",
    )
    meaning = load_json_fixture(
        "ms.skill.customer_meaning_extraction",
        "tests/fixtures/output_valid_extraction.json",
    )
    substantiation = load_json_fixture(
        "ms.skill.claim_substantiation",
        "tests/fixtures/output_valid_substantiation.json",
    )
    offer = load_json_fixture(
        "ms.skill.offer_builder",
        "tests/fixtures/output_proceed_preferred.json",
    )
    assert validate_interview_output_semantics(interview) == []
    assert validate_meaning_output_semantics(meaning) == []
    assert validate_substantiation_semantics(substantiation) == []
    assert validate_offer_output_semantics(offer) == []
