"""SKILL-02.8 — Offer Builder 0.1.0 tests."""

from __future__ import annotations

from app.schemas.contracts import SkillLifecycleStatus
from app.skills.legacy_output_contract import expected_frozen_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from tests.support.archive_mkt_validation import (
    PACKAGE_HASHES,
    load_json_fixture,
    package_hash,
    read_manifest_text,
    saas_catalog,
    schema_validator,
    validate_offer_output_semantics,
)

SKILL_ID = "ms.skill.offer_builder"
PKG_HASH = PACKAGE_HASHES[SKILL_ID]


def test_01_package_validates() -> None:
    from tests.support.archive_mkt_validation import package_root

    assert validate_skill_package(package_root(SKILL_ID)).valid is True


def test_02_preferred_offer_substantiated_claims() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_proceed_preferred.json")
    schema_validator(SKILL_ID, "output.schema.json").validate(data)
    assert validate_offer_output_semantics(data, cim_catalog=saas_catalog()) == []


def test_03_mv_stop_blocks_preferred() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_mv_stop_blocked.json")
    assert data["preferred_offer_id"] is None
    assert data["offer_readiness"] == "blocked"
    assert all(offer.get("status") != "preferred" for offer in data["offer_candidates"])
    bad = dict(data)
    bad["preferred_offer_id"] = "offer-blocked-1"
    bad["offer_candidates"] = [
        {**data["offer_candidates"][0], "status": "preferred"},
    ]
    errors = validate_offer_output_semantics(bad, mv_verdict="stop", cim_catalog=saas_catalog())
    assert len(errors) >= 1


def test_04_mv_defer_exploratory_only() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_mv_defer_exploratory.json")
    assert data["offer_readiness"] == "exploratory_only"
    errors = validate_offer_output_semantics(data, mv_verdict="defer", cim_catalog=saas_catalog())
    assert not any("ready_for_owner_review" in str(data["offer_readiness"]) and "defer" in e for e in errors)


def test_05_no_campaign_or_execution_fields() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_proceed_preferred.json")
    for field in ("campaign", "execution_status", "publication", "approval_granted"):
        assert field not in data


def test_06_human_approval_required() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_proceed_preferred.json")
    assert data["human_approval_required"] is True


def test_07_registry_candidate() -> None:
    from tests.support.archive_mkt_validation import package_root

    projection = project_validation_report(validate_skill_package(package_root(SKILL_ID)))
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE
    assert derive_eligibility_view(projection.version_record).production_eligible is False


def test_08_deterministic_hash() -> None:
    assert package_hash(SKILL_ID) == PKG_HASH


def test_09_all_frozen_upstream_hashes_present() -> None:
    for skill_id, version in (
        ("ms.skill.positioning", "0.1.0"),
        ("ms.skill.market_validation", "0.2.0"),
    ):
        assert expected_frozen_package_hash(skill_id, version) is not None
