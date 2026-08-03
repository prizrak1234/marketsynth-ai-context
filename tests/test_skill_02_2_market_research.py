"""SKILL-02.2 — Market Research native package tests."""

from __future__ import annotations

import json

import pytest
from app.audit import (
    AuditDecisionReadiness,
    adapt_package_validation_report,
    derive_decision_readiness,
)
from app.audit.contracts import AuditType
from app.lineage.builders import build_package_validation_lineage
from app.schemas.contracts import SkillLifecycleStatus, SkillOutputContractType
from app.skills.hashing import calculate_skill_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from jsonschema.exceptions import ValidationError
from tests.support.market_research_validation import (
    FROZEN_PACKAGE_HASH,
    PACKAGE_ROOT,
    ResearchStatus,
    load_json_fixture,
    output_has_verdict_or_readiness,
    package_structure_valid,
    parse_manifest_scalar,
    read_manifest_text,
    validate_finding_schema,
    validate_input_schema,
    validate_output_fixture,
    validate_output_schema,
)
from tests.support.product_marketing_context_validation import (
    FROZEN_MARKET_VALIDATION_HASH,
    FROZEN_MARKET_VALIDATION_ROOT,
)

MANIFEST = read_manifest_text()


def test_01_package_validates_through_production_validator() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    assert report.valid is True
    assert report.skill_id == "ms.skill.market_research"
    assert report.manifest is not None
    assert report.manifest.output_contract_type == SkillOutputContractType.RESEARCH


def test_02_status_is_candidate() -> None:
    assert parse_manifest_scalar(MANIFEST, "status") == "candidate"


def test_03_output_contract_type_is_research() -> None:
    assert parse_manifest_scalar(MANIFEST, "output_contract_type") == "research"


def test_04_no_tools_network_scripts() -> None:
    assert "allowed_tools: []" in MANIFEST
    assert "default: deny" in MANIFEST
    assert "enabled: false" in MANIFEST


def test_05_required_pmc_dependency_declared() -> None:
    assert "ms.skill.product_marketing_context" in MANIFEST
    assert "required_dependency" in MANIFEST


def test_06_input_schema_validates_complete_fixture() -> None:
    validate_input_schema(load_json_fixture("tests/fixtures/input_complete.json"))


def test_07_input_schema_validates_partial_fixture() -> None:
    validate_input_schema(load_json_fixture("tests/fixtures/input_partial.json"))


def test_08_input_requires_product_marketing_context() -> None:
    with pytest.raises(ValidationError):
        validate_input_schema({"research_objectives": ["Only objectives"]})


def test_09_finding_verified_without_source_rejected() -> None:
    data = load_json_fixture("tests/fixtures/finding_invalid_verified_no_source.json")
    with pytest.raises(ValidationError):
        validate_finding_schema(data)


def test_10_output_partially_complete_validates() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_partially_complete.json")
    )
    assert parsed.research_status == ResearchStatus.PARTIALLY_COMPLETE


def test_11_output_insufficient_sources_validates() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_insufficient_sources.json")
    )
    assert parsed.research_status == ResearchStatus.INSUFFICIENT_SOURCES


def test_12_invalid_commercial_research_status_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_output_schema(
            load_json_fixture("tests/fixtures/output_invalid_commercial_status.json")
        )


def test_13_no_verdict_or_readiness_in_output_schema() -> None:
    schema = json.loads((PACKAGE_ROOT / "schemas/output.schema.json").read_text(encoding="utf-8"))
    assert "verdict" not in schema.get("properties", {})
    assert "readiness" not in schema.get("properties", {})


def test_14_output_fixtures_have_no_verdict_or_readiness() -> None:
    for path in (
        "tests/fixtures/output_partially_complete.json",
        "tests/fixtures/output_insufficient_sources.json",
    ):
        assert not output_has_verdict_or_readiness(load_json_fixture(path))


def test_15_finding_separates_inference_flag() -> None:
    output = load_json_fixture("tests/fixtures/output_partially_complete.json")
    inferences = [item for item in output["inferences"] if item.get("inference")]
    assert inferences
    for item in inferences:
        assert item["verification_status"] != "verified"


def test_16_source_context_reference_preserved() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_partially_complete.json")
    )
    ref = parsed.source_context_reference
    assert ref["skill_id"] == "ms.skill.product_marketing_context"
    assert ref["output_hash"]


def test_17_output_contains_skill_id_version_hashes_provenance() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_partially_complete.json")
    )
    assert parsed.skill_id == "ms.skill.market_research"
    assert parsed.skill_version == "0.1.0"
    assert len(parsed.input_hash) == 64
    assert len(parsed.output_hash) == 64
    assert parsed.provenance.skill_id == "ms.skill.market_research"


def test_18_registry_projection_candidate_not_production_eligible() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    projection = project_validation_report(report)
    assert projection.version_record is not None
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE
    eligibility = derive_eligibility_view(projection.version_record)
    assert eligibility.production_eligible is False


def test_19_audit_ready_for_audit_not_activation() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    readiness = derive_decision_readiness(
        audit_type=AuditType.PACKAGE_VALIDATION,
        findings=audit.findings,
        report_status=audit.status,
        package_valid=report.valid,
    )
    assert readiness == AuditDecisionReadiness.READY_FOR_AUDIT


def test_20_lineage_graph_builds_in_memory() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    graph = build_package_validation_lineage(report, audit_report=audit)
    assert graph.graph_hash


def test_21_frozen_market_validation_unchanged() -> None:
    mv_hash = calculate_skill_package_hash(FROZEN_MARKET_VALIDATION_ROOT)
    assert mv_hash == FROZEN_MARKET_VALIDATION_HASH


def test_22_package_hash_deterministic() -> None:
    h1 = calculate_skill_package_hash(PACKAGE_ROOT)
    h2 = calculate_skill_package_hash(PACKAGE_ROOT)
    assert h1 == h2 == FROZEN_PACKAGE_HASH


def test_23_package_structure_valid() -> None:
    assert package_structure_valid()


def test_24_skill_md_instruction_only() -> None:
    skill_md = (PACKAGE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "source" in skill_md.lower()
    assert "allowed_tools" not in skill_md
    assert "Prohibited behavior" in skill_md


def test_25_output_extra_verdict_field_rejected_by_schema() -> None:
    data = load_json_fixture("tests/fixtures/output_partially_complete.json")
    data["verdict"] = "proceed"
    with pytest.raises(ValidationError):
        validate_output_schema(data)


def test_26_evidence_gaps_required_in_output() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_partially_complete.json")
    )
    assert parsed.evidence_gaps


def test_27_research_questions_present() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_partially_complete.json")
    )
    assert parsed.research_questions


def test_28_coverage_and_evidence_quality_present() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_partially_complete.json")
    )
    assert parsed.coverage in {"full", "partial", "minimal", "unknown"}
    assert parsed.evidence_quality in {
        "comprehensive",
        "partial",
        "insufficient",
        "conflicted",
        "unknown",
    }
