"""SKILL-02.6B — Market Validation 0.2.0 native package tests."""

from __future__ import annotations

import copy

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
from tests.support.competitor_analysis_validation import FROZEN_PMC_010_HASH
from tests.support.icp_segmentation_validation import FROZEN_CA_HASH
from tests.support.icp_segmentation_validation import FROZEN_PACKAGE_HASH as FROZEN_ICP_HASH
from tests.support.market_validation_v020_validation import (
    CIM_BUNDLE_HASH,
    CIM_URI,
    FROZEN_MV_010_HASH,
    MV_ROOT,
    PACKAGE_ROOT,
    MarketValidationVerdict,
    load_json_fixture,
    offer_consumer_respects_blockers,
    output_has_forbidden_fields,
    package_hash,
    package_structure_valid,
    parse_manifest_scalar,
    positioning_consumer_reads_mv,
    read_manifest_text,
    validate_blocker_schema,
    validate_condition_schema,
    validate_dimension_schema,
    validate_input_schema,
    validate_output_fixture,
    validate_output_fixture_schema_only,
    validate_output_semantics,
    validate_readiness_schema,
    validate_risk_schema,
)
from tests.support.product_marketing_context_validation import (
    PACKAGE_ROOT as PMC_010_ROOT,
)

MANIFEST = read_manifest_text()
MV_020_HASH = "ec7c86ce0bc39b5481e336b7749de3cf087d47630be315c639897dd687568f7a"
MR_HASH = "6acce32a4952de75d97129d8d39cc15c14a97805fc8850927bac3c19cc6fc14e"
PMC_020_HASH = "08bf9d55a261da52a8659f5aa6f06c3f9a63f13f06a21aea5b2416b10a381eaa"


def test_01_package_validates_through_production_validator() -> None:
    assert package_structure_valid()
    report = validate_skill_package(PACKAGE_ROOT)
    assert report.valid is True
    assert report.skill_id == "ms.skill.market_validation"
    assert report.manifest is not None
    assert report.manifest.output_contract_type == SkillOutputContractType.DECISION


def test_02_version_is_020() -> None:
    assert parse_manifest_scalar(MANIFEST, "version") == "0.2.0"


def test_03_status_candidate() -> None:
    assert parse_manifest_scalar(MANIFEST, "status") == "candidate"


def test_04_output_contract_type_decision() -> None:
    assert parse_manifest_scalar(MANIFEST, "output_contract_type") == "decision"


def test_05_no_tools() -> None:
    assert "allowed_tools: []" in MANIFEST


def test_06_network_denied() -> None:
    assert "default: deny" in MANIFEST


def test_07_scripts_disabled() -> None:
    assert "enabled: false" in MANIFEST


def test_08_input_schema_valid() -> None:
    validate_input_schema(load_json_fixture("tests/fixtures/input_upstream_refs.json"))


def test_09_output_schema_valid() -> None:
    validate_output_fixture(load_json_fixture("tests/fixtures/output_proceed.json"))


def test_10_decision_readiness_schema_valid() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed.json")
    validate_readiness_schema(data["decision_readiness"])


def test_11_decision_dimension_schema_valid() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed.json")
    validate_dimension_schema(data["decision_dimensions"][0])


def test_12_hard_blocker_schema_valid() -> None:
    data = load_json_fixture("tests/fixtures/output_stop.json")
    validate_blocker_schema(data["blockers"][0])


def test_13_condition_schema_valid() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed_with_conditions.json")
    validate_condition_schema(data["conditions"][0])


def test_14_risk_schema_valid() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed.json")
    validate_risk_schema(data["noncritical_risks"][0])


def test_15_pmc_dependency_range_explicit() -> None:
    assert ">=0.2.0" in MANIFEST
    assert "0.1.0 not compatible" in MANIFEST


def test_16_mr_dependency_range_explicit() -> None:
    assert "ms.skill.market_research" in MANIFEST
    assert ">=0.1.0" in MANIFEST


def test_17_ca_dependency_range_explicit() -> None:
    assert "ms.skill.competitor_analysis" in MANIFEST


def test_18_cim_version_range_explicit() -> None:
    assert "CIM schema >=0.1.0" in MANIFEST


def test_19_missing_dependency_identity_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/input_upstream_refs.json"))
    del data["market_research_output"]["source_skill_id"]
    with pytest.raises(ValidationError):
        validate_input_schema(data)


def test_20_missing_dependency_version_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/input_upstream_refs.json"))
    del data["competitor_analysis_output"]["source_skill_version"]
    with pytest.raises(ValidationError):
        validate_input_schema(data)


def test_21_missing_dependency_output_hash_rejected() -> None:
    with pytest.raises(ValidationError):
        validate_input_schema(load_json_fixture("tests/fixtures/input_missing_hash.json"))


def test_22_missing_cim_hash_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/input_upstream_refs.json"))
    del data["customer_intelligence_reference"]["cim_document_hash"]
    with pytest.raises(ValidationError):
        validate_input_schema(data)


def test_23_shared_cim_uri_required() -> None:
    data = load_json_fixture("tests/fixtures/input_upstream_refs.json")
    assert data["customer_intelligence_reference"]["cim_schema_uri"] == CIM_URI


def test_24_proceed_fixture_validates() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_proceed.json"))
    assert parsed.verdict == MarketValidationVerdict.PROCEED


def test_25_proceed_with_conditions_fixture_validates() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_proceed_with_conditions.json")
    )
    assert parsed.verdict == MarketValidationVerdict.PROCEED_WITH_CONDITIONS
    assert parsed.conditions


def test_26_revise_segment_fixture_validates() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_revise_segment.json"))
    assert parsed.verdict == MarketValidationVerdict.REVISE


def test_27_revise_pricing_fixture_validates() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_revise_pricing.json"))
    assert parsed.verdict == MarketValidationVerdict.REVISE


def test_28_defer_fixture_validates() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_defer.json"))
    assert parsed.verdict == MarketValidationVerdict.DEFER


def test_29_stop_fixture_validates() -> None:
    parsed = validate_output_fixture(load_json_fixture("tests/fixtures/output_stop.json"))
    assert parsed.verdict == MarketValidationVerdict.STOP


def test_30_insufficient_evidence_fixture_validates() -> None:
    parsed = validate_output_fixture(
        load_json_fixture("tests/fixtures/output_insufficient_evidence.json")
    )
    assert parsed.verdict == MarketValidationVerdict.INSUFFICIENT_EVIDENCE


def test_31_conflicted_fixture_validates_schema() -> None:
    parsed = validate_output_fixture_schema_only(
        load_json_fixture("tests/fixtures/output_conflicted_upstream.json")
    )
    assert parsed.decision_readiness["readiness"] == "conflicted"


def test_32_missing_cim_cannot_produce_proceed() -> None:
    with pytest.raises(ValidationError):
        validate_input_schema(load_json_fixture("tests/fixtures/input_missing_cim.json"))


def test_33_proceed_with_critical_blocker_rejected() -> None:
    with pytest.raises(ValueError, match="critical blocker"):
        validate_output_fixture(
            load_json_fixture("tests/fixtures/output_invalid_proceed_with_blocker.json")
        )


def test_34_proceed_with_insufficient_readiness_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed.json"))
    data["decision_readiness"]["readiness"] = "insufficient_evidence"
    assert "insufficient readiness" in validate_output_semantics(data)[0]


def test_35_proceed_with_conditions_empty_conditions_rejected() -> None:
    with pytest.raises(ValueError, match="conditions"):
        validate_output_fixture(
            load_json_fixture("tests/fixtures/output_invalid_conditions_empty.json")
        )


def test_36_revise_empty_required_changes_rejected() -> None:
    with pytest.raises(ValueError, match="required_changes"):
        validate_output_fixture(
            load_json_fixture("tests/fixtures/output_invalid_revise_no_changes.json")
        )


def test_37_defer_missing_reason_rejected() -> None:
    with pytest.raises(ValueError, match="defer_reason"):
        validate_output_fixture(
            load_json_fixture("tests/fixtures/output_invalid_defer_no_reason.json")
        )


def test_38_stop_no_blocker_rejected() -> None:
    with pytest.raises(ValueError, match="blocker"):
        validate_output_fixture(
            load_json_fixture("tests/fixtures/output_invalid_stop_no_blocker.json")
        )


def test_39_stop_inference_only_rejected() -> None:
    errors = validate_output_semantics(
        load_json_fixture("tests/fixtures/output_invalid_stop_inference_only.json")
    )
    assert any("inference" in err for err in errors)


def test_40_insufficient_evidence_no_gaps_rejected() -> None:
    with pytest.raises(ValueError, match="evidence_gaps"):
        validate_output_fixture(
            load_json_fixture("tests/fixtures/output_invalid_insufficient_no_gaps.json")
        )


def test_41_high_confidence_no_provenance_rejected() -> None:
    errors = validate_output_semantics(
        load_json_fixture("tests/fixtures/output_invalid_high_confidence_no_provenance.json")
    )
    assert any("provenance" in err for err in errors)


def test_42_verdict_without_evidence_rejected() -> None:
    with pytest.raises(ValueError, match="supporting evidence"):
        validate_output_fixture(
            load_json_fixture("tests/fixtures/output_invalid_proceed_empty_evidence.json")
        )


def test_43_output_contains_all_source_references() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed.json")
    for key in (
        "source_context_reference",
        "source_research_reference",
        "source_competitor_reference",
        "source_cim_reference",
    ):
        assert data[key]["source_output_hash"]


def test_44_upstream_evidence_references_preserved() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed.json")
    assert data["source_cim_reference"]["source_evidence_references"]


def test_45_upstream_unknowns_preserved() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed.json")
    assert data["source_cim_reference"]["source_unknowns"]


def test_46_upstream_conflicts_preserved() -> None:
    data = load_json_fixture("tests/fixtures/output_conflicted_upstream.json")
    assert data["conflicts"]


def test_47_cim_selected_segment_ids_preserved() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed.json")
    assert "seg-remote-eng" in data["source_cim_reference"]["selected_segment_ids"]


def test_48_verdict_enum_finite() -> None:
    assert len(MarketValidationVerdict) == 6


def test_49_forbidden_positioning_field_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed.json"))
    data["positioning"] = "hypothesis"
    assert "positioning" in output_has_forbidden_fields(data)
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture_schema_only(data)


def test_50_forbidden_offer_field_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed.json"))
    data["final_offer"] = "offer"
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture_schema_only(data)


def test_51_forbidden_campaign_field_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed.json"))
    data["campaign"] = "campaign"
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture_schema_only(data)


def test_52_forbidden_execution_status_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed.json"))
    data["execution_status"] = "running"
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture_schema_only(data)


def test_53_human_approval_required_present() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed.json")
    assert data["human_approval_required"] is True


def test_54_proceed_does_not_imply_approval_granted() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed.json")
    assert data.get("approval_granted") is not True


def test_55_cwf_proceed_mapping_fixture_validates() -> None:
    mapping = load_json_fixture("tests/fixtures/cwf_mapping_proceed.json")
    assert mapping["compatibility"] == "compatible"


def test_56_cwf_reject_stop_mapping_adapter_required() -> None:
    mapping = load_json_fixture("tests/fixtures/cwf_mapping_reject_stop.json")
    assert mapping["adapter_required"] is True


def test_57_defer_mapping_no_direct_equivalent() -> None:
    mapping = load_json_fixture("tests/fixtures/cwf_mapping_defer_unknown.json")
    assert mapping["compatibility"] == "unknown"


def test_58_positioning_consumer_stub_reads_allowed_fields() -> None:
    consumer = load_json_fixture("tests/fixtures/positioning_consumer_stub.json")
    output = load_json_fixture("tests/fixtures/output_proceed_with_conditions.json")
    result = positioning_consumer_reads_mv(consumer, output)
    assert result["segment_ids"]


def test_59_positioning_cannot_reinterpret_stop() -> None:
    consumer = load_json_fixture("tests/fixtures/positioning_consumer_stub.json")
    consumer = copy.deepcopy(consumer)
    consumer["verdict_consumed"] = "proceed"
    output = load_json_fixture("tests/fixtures/output_stop.json")
    with pytest.raises(ValueError, match="stop"):
        positioning_consumer_reads_mv(consumer, output)


def test_60_offer_consumer_cannot_ignore_blockers() -> None:
    consumer = load_json_fixture("tests/fixtures/offer_consumer_stub.json")
    offer_consumer_respects_blockers(consumer)
    bad = copy.deepcopy(consumer)
    bad["blockers_ignored"] = ["HB-004"]
    with pytest.raises(ValueError, match="blockers"):
        offer_consumer_respects_blockers(bad)


def test_61_registry_projection_candidate() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    projection = project_validation_report(report)
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_62_production_eligibility_false() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    projection = project_validation_report(report)
    eligibility = derive_eligibility_view(projection.version_record)
    assert eligibility.production_eligible is False


def test_63_audit_readiness_ready_for_audit() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    readiness = derive_decision_readiness(
        audit_type=AuditType.PACKAGE_VALIDATION,
        findings=audit.findings,
        report_status=audit.status,
        package_valid=report.valid,
    )
    assert readiness == AuditDecisionReadiness.READY_FOR_AUDIT


def test_64_lineage_graph_builds_from_four_upstream() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    graph = build_package_validation_lineage(report, audit_report=audit)
    assert graph.graph_hash


def test_65_lineage_preserves_parent_hashes() -> None:
    lineage = load_json_fixture("tests/fixtures/lineage_four_upstream.json")
    assert len(lineage["parents"]) == 4


def test_66_package_hash_deterministic() -> None:
    assert package_hash() == MV_020_HASH == calculate_skill_package_hash(PACKAGE_ROOT)


def test_67_mv_010_frozen_hash_unchanged() -> None:
    assert calculate_skill_package_hash(MV_ROOT) == FROZEN_MV_010_HASH
    assert FROZEN_PACKAGE_HASHES[("ms.skill.market_validation", "0.1.0")] == FROZEN_MV_010_HASH


def test_68_all_other_frozen_package_hashes_unchanged() -> None:
    assert calculate_skill_package_hash(PMC_010_ROOT) == FROZEN_PMC_010_HASH
    assert calculate_skill_package_hash(PMC_010_ROOT / "0.2.0") == PMC_020_HASH
    assert calculate_skill_package_hash(
        MV_ROOT.parent / "ms.skill.market_research"
    ) == MR_HASH
    assert calculate_skill_package_hash(
        MV_ROOT.parent / "ms.skill.competitor_analysis"
    ) == FROZEN_CA_HASH
    assert calculate_skill_package_hash(
        MV_ROOT.parent / "ms.skill.icp_segmentation"
    ) == FROZEN_ICP_HASH
    from app.knowledge.cim_hashing import compute_bundle_hash
    from tests.support.cim_shared_schema_validation import load_freeze_manifest

    manifest = load_freeze_manifest()
    assert compute_bundle_hash(manifest["file_hashes"]) == CIM_BUNDLE_HASH


def test_69_version_compatibility_distinct_hashes() -> None:
    assert MV_020_HASH != FROZEN_MV_010_HASH
    assert FROZEN_PACKAGE_HASHES[("ms.skill.market_validation", "0.2.0")] == MV_020_HASH
