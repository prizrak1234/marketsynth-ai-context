"""ARCHIVE-MKT-01.4 — Claim Substantiation 0.1.0 tests."""

from __future__ import annotations

from app.schemas.contracts import SkillLifecycleStatus
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from tests.support.archive_mkt_validation import (
    PACKAGE_HASHES,
    load_json_fixture,
    package_hash,
    read_manifest_text,
    schema_validator,
    validate_substantiation_semantics,
)

SKILL_ID = "ms.skill.claim_substantiation"
PKG_HASH = PACKAGE_HASHES[SKILL_ID]


def test_01_package_validates() -> None:
    from tests.support.archive_mkt_validation import package_root

    assert validate_skill_package(package_root(SKILL_ID)).valid is True


def test_02_prohibited_income_claim() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_valid_substantiation.json")
    assert "claim-income-bad" in data["prohibited_claims"]


def test_03_safety_prohibited_fixture() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_safety_prohibited.json")
    errors = validate_substantiation_semantics(data)
    assert errors == [] or all("prohibited" not in e or "not rejected" not in e for e in errors)
    assessment = data["claim_assessments"][0]
    assert assessment["substantiation_status"] == "prohibited"


def test_04_risk_reversal_not_outcome_proof() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_valid_substantiation.json")
    for rr in data["risk_reversal_candidates"]:
        assert rr.get("proves_outcome") is False


def test_05_offer_builder_inputs_only_substantiated() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_valid_substantiation.json")
    for item in data["offer_builder_claim_inputs"]:
        assert item["substantiation_status"] in {
            "supported",
            "supported_with_conditions",
            "partially_supported",
        }


def test_06_registry_candidate() -> None:
    from tests.support.archive_mkt_validation import package_root

    projection = project_validation_report(validate_skill_package(package_root(SKILL_ID)))
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_07_deterministic_hash() -> None:
    assert package_hash(SKILL_ID) == PKG_HASH
