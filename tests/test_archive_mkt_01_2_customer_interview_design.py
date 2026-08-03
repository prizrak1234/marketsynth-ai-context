"""ARCHIVE-MKT-01.2 — Customer Interview Design 0.1.0 tests."""

from __future__ import annotations

import pytest
from app.audit import adapt_package_validation_report, derive_decision_readiness
from app.lineage.builders import build_package_validation_lineage
from app.schemas.contracts import SkillLifecycleStatus, SkillOutputContractType
from app.skills.legacy_output_contract import expected_frozen_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from jsonschema.exceptions import ValidationError
from tests.support.archive_mkt_validation import (
    PACKAGE_HASHES,
    load_json_fixture,
    package_hash,
    parse_manifest_scalar,
    read_manifest_text,
    schema_validator,
    validate_interview_output_semantics,
)

SKILL_ID = "ms.skill.customer_interview_design"
MANIFEST = read_manifest_text(SKILL_ID)
PKG_HASH = PACKAGE_HASHES[SKILL_ID]


def test_01_package_validates() -> None:
    from tests.support.archive_mkt_validation import package_root

    report = validate_skill_package(package_root(SKILL_ID))
    assert report.valid is True
    assert report.manifest.output_contract_type == SkillOutputContractType.RESEARCH


def test_02_candidate_non_executable() -> None:
    assert parse_manifest_scalar(MANIFEST, "status") == "candidate"
    assert "allowed_tools: []" in MANIFEST
    assert "default: deny" in MANIFEST
    assert "enabled: false" in MANIFEST


def test_03_output_schema_valid() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_valid_guide.json")
    schema_validator(SKILL_ID, "output.schema.json").validate(data)


def test_04_no_invented_answers() -> None:
    bad = load_json_fixture(SKILL_ID, "tests/fixtures/output_invented_answers.json")
    errors = validate_interview_output_semantics(bad)
    assert any("invented answers" in e for e in errors)


def test_05_question_not_customer_evidence() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_valid_guide.json")
    for q in data["questions"]:
        assert q["expected_evidence_type"] == "user_statement"


def test_06_no_viability_verdict_or_offer() -> None:
    data = load_json_fixture(SKILL_ID, "tests/fixtures/output_valid_guide.json")
    assert validate_interview_output_semantics(data) == []


def test_07_registry_projection_candidate() -> None:
    from tests.support.archive_mkt_validation import package_root

    report = validate_skill_package(package_root(SKILL_ID))
    projection = project_validation_report(report)
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE
    eligibility = derive_eligibility_view(projection.version_record)
    assert eligibility.production_eligible is False


def test_08_deterministic_package_hash() -> None:
    assert package_hash(SKILL_ID) == PKG_HASH
    assert package_hash(SKILL_ID) == PKG_HASH


def test_09_frozen_upstream_hashes_unchanged() -> None:
    assert expected_frozen_package_hash("ms.skill.positioning", "0.1.0") == (
        "cbd8283f4addaa9c8496504a9c6dbccd580e8ca317b2cf86bf628be6557e8da6"
    )


def test_10_lineage_builds() -> None:
    from tests.support.archive_mkt_validation import package_root

    report = validate_skill_package(package_root(SKILL_ID))
    lineage = build_package_validation_lineage(report)
    assert lineage.nodes
