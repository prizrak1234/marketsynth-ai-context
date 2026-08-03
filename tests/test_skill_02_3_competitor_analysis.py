"""SKILL-02.3 — Competitor Analysis native package tests."""

from __future__ import annotations

import copy
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
from app.skills.legacy_output_contract import FROZEN_PACKAGE_HASHES
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from jsonschema.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError
from tests.support.competitor_analysis_validation import (
    FROZEN_MV_HASH,
    FROZEN_PMC_010_HASH,
    MR_ROOT,
    PACKAGE_ROOT,
    PMC_020_ROOT,
    ResearchStatus,
    load_json_fixture,
    output_has_forbidden_discriminators,
    package_hash,
    package_structure_valid,
    parse_manifest_scalar,
    read_manifest_text,
    validate_comparison_schema,
    validate_competitor_schema,
    validate_input_schema,
    validate_output_fixture,
)
from tests.support.product_marketing_context_validation import (
    FROZEN_MARKET_VALIDATION_ROOT,
)
from tests.support.product_marketing_context_validation import (
    PACKAGE_ROOT as PMC_010_ROOT,
)

MANIFEST = read_manifest_text()
CA_HASH = "14903c8744b57c472bf09875a41d4b825f175c5cb8ae55eecfdce1829a48cde0"


def test_01_package_validates_through_production_validator() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    assert report.valid is True
    assert report.skill_id == "ms.skill.competitor_analysis"
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


def test_05_input_schema_validates_complete_saas_fixture() -> None:
    validate_input_schema(load_json_fixture("tests/fixtures/input_complete_saas.json"))


def test_06_output_schema_validates_complete_saas_fixture() -> None:
    validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))


def test_07_competitor_schema_validates_direct_record() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_saas.json")
    validate_competitor_schema(data["competitor_inventory"][0])


def test_08_comparison_schema_validates_dimension() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_saas.json")
    validate_comparison_schema(data["comparison_dimensions"][0])


def test_09_complete_saas_fixture_validates() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.research_status == ResearchStatus.COMPLETE


def test_10_cafe_fixture_validates() -> None:
    validate_input_schema(load_json_fixture("tests/fixtures/input_complete_cafe.json"))
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_cafe.json"))
    assert len(parsed.competitor_inventory) == 3


def test_11_sparse_evidence_fixture_validates() -> None:
    fixture = load_json_fixture("tests/fixtures/output_sparse_evidence.json")
    parsed = validate_output_fixture(fixture)
    assert parsed.research_status == ResearchStatus.INSUFFICIENT_SOURCES


def test_12_conflicted_pricing_fixture_validates() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_contradictory_pricing.json")
    )
    assert parsed.research_status == ResearchStatus.CONFLICTED


def test_13_unknown_competitor_type_accepted() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_unknown_competitor_type.json")
    )
    assert parsed.competitor_inventory[0]["competitor_type"] == "unknown"


def test_14_invalid_competitor_type_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_competitor_schema(load_json_fixture("tests/fixtures/competitor_invalid_type.json"))


def test_15_dependency_pmc_version_constraint_in_manifest() -> None:
    assert ">=0.2.0" in MANIFEST
    assert "0.1.0 not compatible" in MANIFEST


def test_16_dependency_market_research_constraint_in_manifest() -> None:
    assert "ms.skill.market_research" in MANIFEST
    assert ">=0.1.0" in MANIFEST


def test_17_input_rejects_pmc_010() -> None:
    with pytest.raises(ValidationError):
        validate_input_schema(load_json_fixture("tests/fixtures/input_invalid_pmc_010.json"))


def test_18_input_missing_source_skill_id_rejected() -> None:
    data = load_json_fixture("tests/fixtures/input_upstream_refs.json")
    bad = copy.deepcopy(data)
    del bad["product_marketing_context"]["source_skill_id"]
    with pytest.raises(ValidationError):
        validate_input_schema(bad)


def test_19_input_missing_source_skill_version_rejected() -> None:
    data = load_json_fixture("tests/fixtures/input_upstream_refs.json")
    bad = copy.deepcopy(data)
    del bad["market_research_output"]["source_skill_version"]
    with pytest.raises(ValidationError):
        validate_input_schema(bad)


def test_20_input_missing_source_output_hash_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_input_schema(load_json_fixture("tests/fixtures/input_invalid_missing_hash.json"))


def test_21_upstream_evidence_references_preserved() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.source_context_reference.get("source_evidence_references")
    assert parsed.source_research_reference.get("source_evidence_references")


def test_22_upstream_unknowns_preserved() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.source_context_reference.get("source_unknowns")
    assert parsed.source_research_reference.get("source_unknowns")


def test_23_upstream_conflicts_preserved_in_conflicted_fixture() -> None:
    validate_input_schema(load_json_fixture("tests/fixtures/input_conflicted_research.json"))
    out = load_json_fixture("tests/fixtures/output_conflicted_research.json")
    parsed = validate_output_fixture(out)
    assert parsed.conflicts


def test_24_no_competitors_claim_not_verified() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_no_competitors_claim.json")
    )
    assert parsed.unsupported_competitor_claims
    assert parsed.unsupported_competitor_claims[0]["verification_status"] != "verified"


def test_25_verified_weakness_without_source_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_competitor_schema(
            load_json_fixture("tests/fixtures/competitor_invalid_verified_weakness.json")
        )


def test_26_output_contains_research_status() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.research_status == ResearchStatus.COMPLETE


def test_27_output_contains_evidence_quality() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.evidence_quality == "comprehensive"


def test_28_output_contains_coverage() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.coverage == "full"


def test_29_output_contains_evidence_gaps() -> None:
    fixture = load_json_fixture("tests/fixtures/output_sparse_evidence.json")
    parsed = validate_output_fixture(fixture)
    assert parsed.evidence_gaps


def test_30_output_with_verdict_rejected_by_pydantic() -> None:
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture(load_json_fixture("tests/fixtures/output_invalid_verdict.json"))


def test_31_output_schema_forbids_readiness_and_execution_status() -> None:
    schema = json.loads((PACKAGE_ROOT / "schemas/output.schema.json").read_text(encoding="utf-8"))
    props = schema.get("properties", {})
    assert "readiness" not in props
    assert "execution_status" not in props
    assert "verdict" not in props


def test_32_output_with_readiness_rejected() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_saas.json")
    data = copy.deepcopy(data)
    data["readiness"] = "ready"
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture(data)


def test_33_output_with_execution_status_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    data["execution_status"] = "pending"
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture(data)


def test_34_no_viability_decision_fields_in_fixtures() -> None:
    for path in (
        "tests/fixtures/output_complete_saas.json",
        "tests/fixtures/output_complete_cafe.json",
    ):
        assert not output_has_forbidden_discriminators(load_json_fixture(path))


def test_35_differentiation_gap_is_not_positioning() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    gap = parsed.differentiation_gaps[0]
    assert "positioning_candidate_reference" in gap
    assert "positioning_statement" not in gap


def test_36_pricing_finding_preserves_source_date_currency() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    pf = parsed.pricing_findings[0]
    assert pf.get("currency") == "USD"
    assert pf.get("observed_at")
    assert pf.get("source_reference")


def test_37_contradictory_evidence_visible() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_contradictory_pricing.json")
    )
    assert parsed.contradictory_evidence
    assert parsed.conflicts


def test_38_registry_projection_remains_candidate() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    projection = project_validation_report(report)
    assert projection.version_record is not None
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_39_production_eligibility_false() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    projection = project_validation_report(report)
    assert projection.version_record is not None
    eligibility = derive_eligibility_view(projection.version_record)
    assert eligibility.production_eligible is False


def test_40_audit_readiness_ready_for_audit() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    readiness = derive_decision_readiness(
        audit_type=AuditType.PACKAGE_VALIDATION,
        findings=audit.findings,
        report_status=audit.status,
        package_valid=report.valid,
    )
    assert readiness == AuditDecisionReadiness.READY_FOR_AUDIT


def test_41_lineage_graph_builds_with_upstream_identity() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    graph = build_package_validation_lineage(report, audit_report=audit)
    assert graph.graph_hash
    output = load_json_fixture("tests/fixtures/output_complete_saas.json")
    assert output["source_context_reference"]["source_skill_id"] == (
        "ms.skill.product_marketing_context"
    )
    assert output["source_research_reference"]["source_skill_id"] == "ms.skill.market_research"


def test_42_lineage_preserves_source_hashes() -> None:
    output = load_json_fixture("tests/fixtures/output_complete_saas.json")
    assert len(output["source_context_reference"]["source_output_hash"]) == 64
    assert len(output["source_research_reference"]["source_output_hash"]) == 64


def test_43_package_hash_deterministic() -> None:
    h1 = calculate_skill_package_hash(PACKAGE_ROOT)
    h2 = package_hash()
    assert h1 == h2 == CA_HASH


def test_44_frozen_legacy_hashes_unchanged() -> None:
    pmc_hash = calculate_skill_package_hash(PMC_010_ROOT)
    mv_hash = calculate_skill_package_hash(FROZEN_MARKET_VALIDATION_ROOT)
    mr_hash = calculate_skill_package_hash(MR_ROOT)
    assert pmc_hash == FROZEN_PMC_010_HASH == FROZEN_PACKAGE_HASHES[
        ("ms.skill.product_marketing_context", "0.1.0")
    ]
    assert mv_hash == FROZEN_MV_HASH == FROZEN_PACKAGE_HASHES[
        ("ms.skill.market_validation", "0.1.0")
    ]
    assert mr_hash == "6acce32a4952de75d97129d8d39cc15c14a97805fc8850927bac3c19cc6fc14e"


def test_45_downstream_icp_segmentation_fields_preserved() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.competitor_inventory[0]["competitor_id"]
    assert parsed.differentiation_gaps
    assert parsed.assumptions is not None
    assert parsed.unknowns is not None
    assert parsed.conflicts is not None
    assert parsed.provenance.source_context_output_hash
    assert len(parsed.output_hash) == 64


def test_46_downstream_positioning_gap_reference_only() -> None:
    gap = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_complete_saas.json")
    ).differentiation_gaps[0]
    assert gap.get("positioning_candidate_reference")
    assert "final_positioning" not in gap


def test_47_package_structure_valid() -> None:
    assert package_structure_valid()


def test_48_skill_md_instruction_only() -> None:
    skill_md = (PACKAGE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "Prohibited behavior" in skill_md
    assert "allowed_tools" not in skill_md


def test_49_pmc_020_package_still_validates() -> None:
    report = validate_skill_package(PMC_020_ROOT)
    assert report.valid is True


def test_50_market_research_package_still_validates() -> None:
    report = validate_skill_package(MR_ROOT)
    assert report.valid is True
