"""ARCHIVE-MKT-01.3 — Customer Meaning Extraction 0.1.0 tests."""

from __future__ import annotations

from app.schemas.contracts import SkillLifecycleStatus, SkillOutputContractType
from app.skills.legacy_output_contract import expected_frozen_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from tests.support.archive_mkt_validation import (
    PACKAGE_HASHES,
    load_json_fixture,
    package_hash,
    parse_manifest_scalar,
    read_manifest_text,
    saas_catalog,
    schema_validator,
    validate_meaning_output_semantics,
)

SKILL_ID = "ms.skill.customer_meaning_extraction"
PKG_HASH = PACKAGE_HASHES[SKILL_ID]


def test_01_package_validates() -> None:
    from tests.support.archive_mkt_validation import package_root

    report = validate_skill_package(package_root(SKILL_ID))
    assert report.valid is True
    assert report.manifest.output_contract_type == SkillOutputContractType.RESEARCH


def test_02_desire_not_auto_capability() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_valid_extraction.json")
    for dtb in data["desire_to_benefit_maps"]:
        assert dtb["satisfaction_status"] in {
            "supported",
            "partially_supported",
            "unsupported",
            "unknown",
            "conflicted",
        }


def test_03_unsupported_desire_finding() -> None:
    bad = load_json_fixture(SKILL_ID, "tests/fixtures/output_unsupported_as_supported.json")
    errors = validate_meaning_output_semantics(bad, cim_catalog=saas_catalog())
    assert any("unsupported desire marked supported" in e for e in errors)


def test_04_no_final_offer_or_approved_claim() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_valid_extraction.json")
    assert validate_meaning_output_semantics(data, cim_catalog=saas_catalog()) == []


def test_05_source_customer_language_preserved() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_valid_extraction.json")
    assert data["customer_meanings"][0]["customer_language"]


def test_06_candidate_registry() -> None:
    from tests.support.archive_mkt_validation import package_root

    report = validate_skill_package(package_root(SKILL_ID))
    projection = project_validation_report(report)
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE
    assert derive_eligibility_view(projection.version_record).production_eligible is False


def test_07_deterministic_hash() -> None:
    assert package_hash(SKILL_ID) == PKG_HASH


def test_08_frozen_positioning_hash_unchanged() -> None:
    assert expected_frozen_package_hash("ms.skill.positioning", "0.1.0") == (
        "cbd8283f4addaa9c8496504a9c6dbccd580e8ca317b2cf86bf628be6557e8da6"
    )
