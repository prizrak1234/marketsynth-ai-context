"""SKILL-02.4 — ICP & Segmentation native package tests."""

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
from tests.support.competitor_analysis_validation import PACKAGE_ROOT as COMPETITOR_ROOT
from tests.support.competitor_analysis_validation import package_hash as competitor_package_hash
from tests.support.icp_segmentation_validation import (
    FROZEN_CA_HASH,
    FROZEN_MV_HASH,
    FROZEN_PMC_010_HASH,
    FROZEN_PMC_020_HASH,
    MKG_ENTITY_MAPPINGS,
    MKG_RELATION_EXAMPLES,
    MR_ROOT,
    PACKAGE_ROOT,
    PMC_020_ROOT,
    CimReadiness,
    ResearchStatus,
    load_json_fixture,
    market_validation_consumer_reads_cim,
    output_has_forbidden_discriminators,
    package_hash,
    package_structure_valid,
    parse_manifest_scalar,
    positioning_consumer_reads_cim,
    read_manifest_text,
    validate_cim_schema,
    validate_customer_claim_schema,
    validate_customer_segment_schema,
    validate_decision_role_schema,
    validate_input_schema,
    validate_jtbd_schema,
    validate_output_fixture,
)
from tests.support.product_marketing_context_validation import (
    FROZEN_MARKET_VALIDATION_ROOT,
)
from tests.support.product_marketing_context_validation import (
    PACKAGE_ROOT as PMC_010_ROOT,
)

MANIFEST = read_manifest_text()
ICP_HASH = "075a4f1989a9050614babec004dda54a420d7f7bd717d9ac7e8a34b41e8ae71a"


def test_01_package_validates_through_production_validator() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    assert report.valid is True
    assert report.skill_id == "ms.skill.icp_segmentation"
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


def test_07_cim_schema_validates_complete_saas_fixture() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_saas.json")
    validate_cim_schema(data["customer_intelligence"])


def test_08_customer_segment_schema_validates_record() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_saas.json")
    validate_customer_segment_schema(data["customer_intelligence"]["segments"][0])


def test_09_jtbd_schema_validates_record() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_saas.json")
    validate_jtbd_schema(data["customer_intelligence"]["segments"][0]["jobs_to_be_done"][0])


def test_10_decision_role_schema_validates_record() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_saas.json")
    validate_decision_role_schema(data["customer_intelligence"]["segments"][0]["decision_roles"][0])


def test_11_complete_saas_fixture_validates() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.research_status == ResearchStatus.COMPLETE
    assert parsed.customer_intelligence["readiness"] == CimReadiness.READY


def test_12_cafe_fixture_validates() -> None:
    validate_input_schema(load_json_fixture("tests/fixtures/input_complete_cafe.json"))
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_cafe.json"))
    assert len(parsed.customer_intelligence["segments"]) == 3


def test_13_mixed_b2b_b2c_fixture_validates() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_mixed_b2b_b2c.json"))
    roles = parsed.customer_intelligence["segments"][1]["decision_roles"][0]
    assert roles["role_type"] == "user"


def test_14_sparse_evidence_fixture_validates() -> None:
    fixture = load_json_fixture("tests/fixtures/output_sparse_evidence.json")
    parsed = validate_output_fixture(fixture)
    assert parsed.research_status == ResearchStatus.INSUFFICIENT_SOURCES
    assert parsed.customer_intelligence["readiness"] == CimReadiness.INSUFFICIENT


def test_15_conflicted_fixture_validates() -> None:
    fixture = load_json_fixture("tests/fixtures/output_conflicted_interviews.json")
    parsed = validate_output_fixture(fixture)
    assert parsed.research_status == ResearchStatus.CONFLICTED
    assert parsed.customer_intelligence["segment_conflicts"]


def test_16_duplicate_overlap_fixture_validates() -> None:
    fixture = load_json_fixture("tests/fixtures/output_duplicate_overlap.json")
    parsed = validate_output_fixture(fixture)
    conflict = parsed.customer_intelligence["segment_conflicts"][0]
    assert conflict["conflict_type"] == "duplicate_segment"


def test_17_invalid_segment_type_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_customer_segment_schema(load_json_fixture("tests/fixtures/segment_invalid_type.json"))


def test_18_input_rejects_pmc_010() -> None:
    with pytest.raises(ValidationError):
        validate_input_schema(load_json_fixture("tests/fixtures/input_invalid_pmc_010.json"))


def test_19_input_missing_market_research_identity_rejected() -> None:
    data = load_json_fixture("tests/fixtures/input_upstream_refs.json")
    bad = copy.deepcopy(data)
    del bad["market_research_output"]["source_skill_id"]
    with pytest.raises(ValidationError):
        validate_input_schema(bad)


def test_20_input_missing_competitor_analysis_identity_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_input_schema(load_json_fixture("tests/fixtures/input_invalid_missing_competitor.json"))


def test_21_input_missing_source_output_hash_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_input_schema(load_json_fixture("tests/fixtures/input_invalid_missing_hash.json"))


def test_22_upstream_evidence_references_preserved() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.source_context_reference.get("source_evidence_references")
    assert parsed.source_research_reference.get("source_evidence_references")
    assert parsed.source_competitor_reference.get("source_evidence_references")


def test_23_upstream_unknowns_preserved() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.source_context_reference.get("source_unknowns")
    assert parsed.source_research_reference.get("source_unknowns")
    assert parsed.source_competitor_reference.get("source_unknowns")


def test_24_upstream_conflicts_preserved_in_conflicted_fixture() -> None:
    fixture = load_json_fixture("tests/fixtures/output_conflicted_interviews.json")
    parsed = validate_output_fixture(fixture)
    assert parsed.customer_intelligence["segment_conflicts"]


def test_25_verified_pain_without_evidence_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_customer_claim_schema(load_json_fixture("tests/fixtures/claim_invalid_verified_pain.json"))


def test_26_system_inference_cannot_be_verified_by_default() -> None:
    with pytest.raises(ValidationError):
        validate_customer_claim_schema(
            load_json_fixture("tests/fixtures/claim_invalid_inference_verified.json")
        )


def test_27_primary_icp_candidate_references_segment() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    segment_ids = {s["segment_id"] for s in parsed.customer_intelligence["segments"]}
    for icp in parsed.primary_icp_candidates:
        assert icp["segment_id"] in segment_ids


def test_28_excluded_segment_has_explicit_reason() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_saas.json")
    data = copy.deepcopy(data)
    data["excluded_segments"] = [
        {
            "segment_id": "seg-agencies",
            "reason": "Insufficient evidence for primary ICP",
            "priority_tier": "excluded",
        }
    ]
    data["customer_intelligence"]["excluded_or_low_priority_segments"] = data["excluded_segments"]
    parsed = validate_output_fixture(data)
    assert parsed.excluded_segments[0]["reason"]


def test_29_aggregate_priority_tier_is_explainable() -> None:
    saas = load_json_fixture("tests/fixtures/output_complete_saas.json")
    seg = saas["customer_intelligence"]["segments"][0]
    pa = seg["priority_assessment"]
    assert pa["priority_tier"]
    assert pa["tier_rationale"]


def test_30_single_opaque_score_not_only_priority_output() -> None:
    saas = load_json_fixture("tests/fixtures/output_complete_saas.json")
    seg = saas["customer_intelligence"]["segments"][0]
    pa = seg["priority_assessment"]
    assert "strategic_fit" in pa
    assert "problem_intensity" in pa
    assert "priority_tier" in pa
    assert "tier_rationale" in pa
    assert "opaque_score" not in pa


def test_31_research_status_present() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.research_status == ResearchStatus.COMPLETE


def test_32_evidence_quality_present() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.evidence_quality == "partial"


def test_33_coverage_present() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.coverage == "partial"


def test_34_evidence_gaps_present() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.evidence_gaps


def test_35_cim_readiness_present() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    assert parsed.customer_intelligence["readiness"] == CimReadiness.READY


def test_36_output_verdict_rejected() -> None:
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture(load_json_fixture("tests/fixtures/output_invalid_verdict.json"))


def test_37_positioning_field_rejected() -> None:
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture(load_json_fixture("tests/fixtures/output_invalid_positioning.json"))


def test_38_offer_field_rejected() -> None:
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture(load_json_fixture("tests/fixtures/output_invalid_offer.json"))


def test_39_execution_status_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_complete_saas.json"))
    data["execution_status"] = "pending"
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture(data)


def test_40_positioning_consumer_reads_cim_without_rederivation() -> None:
    output = load_json_fixture("tests/fixtures/output_complete_saas.json")
    consumed = positioning_consumer_reads_cim(output)
    stub = load_json_fixture("tests/fixtures/positioning_consumer_stub.json")
    assert consumed["recomputed_fields"] == []
    assert "jobs_to_be_done" in stub["recompute_forbidden"]


def test_41_positioning_consumer_receives_jtbd_pains_objections_trust_drivers() -> None:
    output = load_json_fixture("tests/fixtures/output_complete_saas.json")
    consumed = positioning_consumer_reads_cim(output)
    assert consumed["jtbd"]
    assert consumed["pains"]
    assert consumed["objections"]
    assert consumed["trust_drivers"]


def test_42_market_validation_consumer_receives_segment_priority_evidence() -> None:
    output = load_json_fixture("tests/fixtures/output_complete_saas.json")
    mv = market_validation_consumer_reads_cim(output)
    assert mv["segment_priorities"]
    assert mv["evidence_quality"]
    assert mv["coverage"]


def test_43_market_validation_verdict_remains_absent() -> None:
    output = load_json_fixture("tests/fixtures/output_complete_saas.json")
    mv = market_validation_consumer_reads_cim(output)
    stub = load_json_fixture("tests/fixtures/market_validation_consumer_stub.json")
    assert mv["verdict"] is None
    assert stub["verdict_issued_by_icp"] is False


def test_44_mkg_entity_mappings_documented() -> None:
    skill_md = (PACKAGE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    doc = (PACKAGE_ROOT.parents[2] / "docs" / "skills" / "ms.skill.icp_segmentation.md")
    assert "customer_intelligence" in MKG_ENTITY_MAPPINGS.values()
    assert len(MKG_RELATION_EXAMPLES) >= 10
    assert "CIM consumer" in skill_md or "CIM consumer" in doc.read_text(encoding="utf-8")


def test_45_registry_projection_remains_candidate() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    projection = project_validation_report(report)
    assert projection.version_record is not None
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_46_production_eligibility_false() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    projection = project_validation_report(report)
    assert projection.version_record is not None
    eligibility = derive_eligibility_view(projection.version_record)
    assert eligibility.production_eligible is False


def test_47_audit_readiness_ready_for_audit() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    readiness = derive_decision_readiness(
        audit_type=AuditType.PACKAGE_VALIDATION,
        findings=audit.findings,
        report_status=audit.status,
        package_valid=report.valid,
    )
    assert readiness == AuditDecisionReadiness.READY_FOR_AUDIT


def test_48_lineage_graph_builds_with_triple_upstream() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    graph = build_package_validation_lineage(report, audit_report=audit)
    assert graph.graph_hash
    output = load_json_fixture("tests/fixtures/output_complete_saas.json")
    ctx = output["source_context_reference"]["source_skill_id"]
    assert ctx == "ms.skill.product_marketing_context"
    assert output["source_research_reference"]["source_skill_id"] == "ms.skill.market_research"
    comp = output["source_competitor_reference"]["source_skill_id"]
    assert comp == "ms.skill.competitor_analysis"


def test_49_lineage_preserves_source_hashes() -> None:
    output = load_json_fixture("tests/fixtures/output_complete_saas.json")
    assert len(output["source_context_reference"]["source_output_hash"]) == 64
    assert len(output["source_research_reference"]["source_output_hash"]) == 64
    assert len(output["source_competitor_reference"]["source_output_hash"]) == 64


def test_50_package_hash_deterministic() -> None:
    h1 = calculate_skill_package_hash(PACKAGE_ROOT)
    h2 = package_hash()
    assert h1 == h2 == ICP_HASH


def test_51_frozen_legacy_hashes_unchanged() -> None:
    pmc_hash = calculate_skill_package_hash(PMC_010_ROOT)
    mv_hash = calculate_skill_package_hash(FROZEN_MARKET_VALIDATION_ROOT)
    mr_hash = calculate_skill_package_hash(MR_ROOT)
    ca_hash = calculate_skill_package_hash(COMPETITOR_ROOT)
    pmc_020_hash = calculate_skill_package_hash(PMC_020_ROOT)
    assert pmc_hash == FROZEN_PMC_010_HASH == FROZEN_PACKAGE_HASHES[
        ("ms.skill.product_marketing_context", "0.1.0")
    ]
    assert mv_hash == FROZEN_MV_HASH == FROZEN_PACKAGE_HASHES[
        ("ms.skill.market_validation", "0.1.0")
    ]
    assert mr_hash == "6acce32a4952de75d97129d8d39cc15c14a97805fc8850927bac3c19cc6fc14e"
    assert ca_hash == FROZEN_CA_HASH == competitor_package_hash()
    assert pmc_020_hash == FROZEN_PMC_020_HASH


def test_52_package_structure_valid() -> None:
    assert package_structure_valid()


def test_53_skill_md_instruction_only() -> None:
    skill_md = (PACKAGE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "Prohibited behavior" in skill_md
    assert "allowed_tools" not in skill_md


def test_54_upstream_packages_still_validate() -> None:
    assert validate_skill_package(PMC_020_ROOT).valid is True
    assert validate_skill_package(MR_ROOT).valid is True
    assert validate_skill_package(COMPETITOR_ROOT).valid is True


def test_output_schema_forbids_top_level_readiness() -> None:
    schema = json.loads((PACKAGE_ROOT / "schemas/output.schema.json").read_text(encoding="utf-8"))
    props = schema.get("properties", {})
    assert "readiness" not in props
    assert "verdict" not in props
    assert "positioning" not in props


def test_no_viability_fields_in_valid_fixtures() -> None:
    for path in (
        "tests/fixtures/output_complete_saas.json",
        "tests/fixtures/output_complete_cafe.json",
    ):
        assert not output_has_forbidden_discriminators(load_json_fixture(path))
