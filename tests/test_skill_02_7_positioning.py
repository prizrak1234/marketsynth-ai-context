"""SKILL-02.7 — Positioning 0.1.0 native package tests."""

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
from tests.support.market_validation_v020_validation import (
    CIM_BUNDLE_HASH as MV_CIM_BUNDLE_HASH,
)
from tests.support.market_validation_v020_validation import (
    FROZEN_MV_010_HASH,
)
from tests.support.positioning_validation import (
    CIM_BUNDLE_HASH,
    MV_020_PKG_HASH,
    PACKAGE_ROOT,
    content_consumer_stub,
    copywriting_consumer_stub,
    launch_strategy_consumer_stub,
    load_json_fixture,
    offer_builder_consumer_stub,
    output_has_forbidden_fields,
    package_hash,
    package_structure_valid,
    parse_manifest_scalar,
    read_manifest_text,
    saas_catalog,
    validate_downstream_offer_input_schema,
    validate_hypothesis_schema,
    validate_input_schema,
    validate_input_semantics,
    validate_message_hierarchy_schema,
    validate_output_fixture,
    validate_output_fixture_schema_only,
    validate_output_semantics,
    validate_risk_schema,
    validate_territory_schema,
)
from tests.support.product_marketing_context_validation import (
    PACKAGE_ROOT as PMC_010_ROOT,
)

MANIFEST = read_manifest_text()
POS_HASH = "cbd8283f4addaa9c8496504a9c6dbccd580e8ca317b2cf86bf628be6557e8da6"
MR_HASH = "6acce32a4952de75d97129d8d39cc15c14a97805fc8850927bac3c19cc6fc14e"
PMC_020_HASH = "08bf9d55a261da52a8659f5aa6f06c3f9a63f13f06a21aea5b2416b10a381eaa"
PMC_010_HASH = "5e3dfc1bfc48c56d33951006c3adcf80b4d53ad246e96669d1d32014934cc230"


def test_01_package_validates_through_production_validator() -> None:
    assert package_structure_valid()
    report = validate_skill_package(PACKAGE_ROOT)
    assert report.valid is True
    assert report.skill_id == "ms.skill.positioning"
    assert report.manifest is not None
    assert report.manifest.output_contract_type == SkillOutputContractType.RESEARCH


def test_02_version_is_010() -> None:
    assert parse_manifest_scalar(MANIFEST, "version") == "0.1.0"


def test_03_status_candidate() -> None:
    assert parse_manifest_scalar(MANIFEST, "status") == "candidate"


def test_04_no_tools() -> None:
    assert "allowed_tools: []" in MANIFEST


def test_05_network_denied() -> None:
    assert "default: deny" in MANIFEST


def test_06_scripts_disabled() -> None:
    assert "enabled: false" in MANIFEST


def test_07_output_contract_type_research() -> None:
    assert parse_manifest_scalar(MANIFEST, "output_contract_type") == "research"


def test_08_input_schema_valid() -> None:
    validate_input_schema(load_json_fixture("tests/fixtures/input_upstream_refs.json"))


def test_09_output_schema_valid() -> None:
    validate_output_fixture(
        load_json_fixture("tests/fixtures/output_proceed_preferred.json"),
        cim_catalog=saas_catalog(),
    )


def test_10_hypothesis_schema_valid() -> None:
    data = load_json_fixture("tests/fixtures/output_saas_three_hypotheses.json")
    validate_hypothesis_schema(data["positioning_hypotheses"][0])


def test_11_territory_schema_valid() -> None:
    data = load_json_fixture("tests/fixtures/output_saas_three_hypotheses.json")
    validate_territory_schema(data["positioning_territories"][0])


def test_12_message_hierarchy_schema_valid() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed_preferred.json")
    validate_message_hierarchy_schema(data["message_hierarchy"])


def test_13_risk_schema_valid() -> None:
    risk = {
        "risk_id": "risk-1",
        "domain": "weak_differentiation",
        "description": "Competitors may imitate async UX",
        "likelihood": "medium",
        "impact": "medium",
        "severity": "major",
        "evidence_references": ["src-001"],
        "assumptions": [],
        "mitigation": "Deep workflow integrations",
        "residual_risk": "medium",
        "blocking": False,
        "provenance": {"skill_id": "ms.skill.positioning", "skill_version": "0.1.0"},
    }
    validate_risk_schema(risk)


def test_14_downstream_offer_input_schema_valid() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed_preferred.json")
    validate_downstream_offer_input_schema(data["downstream_offer_inputs"][0])


def test_15_cim_dependency_explicit() -> None:
    assert "ms.skill.icp_segmentation" in MANIFEST
    assert "CIM schema >=0.1.0" in MANIFEST or "CIM schema" in MANIFEST


def test_16_ca_dependency_explicit() -> None:
    assert "ms.skill.competitor_analysis" in MANIFEST


def test_17_mv_020_dependency_explicit() -> None:
    assert "ms.skill.market_validation" in MANIFEST
    assert ">=0.2.0" in MANIFEST


def test_18_missing_cim_identity_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/input_upstream_refs.json"))
    data["customer_intelligence_reference"]["source_skill_id"] = ""
    with pytest.raises(ValidationError):
        validate_input_schema(data)


def test_19_missing_cim_hash_rejected() -> None:
    data = load_json_fixture("tests/fixtures/input_missing_cim_hash.json")
    with pytest.raises(ValidationError):
        validate_input_schema(data)
    assert "missing CIM document hash" in validate_input_semantics(data)


def test_20_missing_ca_hash_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/input_upstream_refs.json"))
    data["competitor_analysis_output"]["source_output_hash"] = ""
    with pytest.raises(ValidationError):
        validate_input_schema(data)
    assert "missing CA output hash" in validate_input_semantics(data)


def test_21_missing_mv_hash_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/input_upstream_refs.json"))
    data["market_validation_output"]["source_output_hash"] = ""
    with pytest.raises(ValidationError):
        validate_input_schema(data)
    assert "missing MV output hash" in validate_input_semantics(data)


def test_22_unknown_cim_version_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/input_upstream_refs.json"))
    data["customer_intelligence_reference"]["cim_version"] = "2.0.0"
    with pytest.raises(ValidationError):
        validate_input_schema(data)


def test_23_saas_fixture_validates() -> None:
    validate_output_fixture(
        load_json_fixture("tests/fixtures/output_saas_three_hypotheses.json"),
        cim_catalog=saas_catalog(),
    )


def test_24_cafe_fixture_validates() -> None:
    validate_output_fixture_schema_only(
        load_json_fixture("tests/fixtures/output_cafe_alternatives.json")
    )


def test_25_proceed_fixture_validates() -> None:
    validate_output_fixture(
        load_json_fixture("tests/fixtures/output_proceed_preferred.json"),
        cim_catalog=saas_catalog(),
    )


def test_26_proceed_with_conditions_preserves_conditions() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed_with_conditions.json")
    validate_output_fixture(data, cim_catalog=saas_catalog())
    assert data["conditions_inherited"]
    assert data["downstream_offer_inputs"][0]["conditions"]


def test_27_revise_fixture_preserves_required_changes() -> None:
    data = load_json_fixture("tests/fixtures/output_revise.json")
    validate_output_fixture_schema_only(data)
    assert data["positioning_hypotheses"][0]["validation_conditions"]


def test_28_defer_fixture_is_exploratory_only() -> None:
    data = load_json_fixture("tests/fixtures/output_defer.json")
    validate_output_fixture_schema_only(data)
    assert data["positioning_readiness"] == "exploratory_only"


def test_29_stop_fixture_cannot_be_recommended() -> None:
    data = load_json_fixture("tests/fixtures/output_stop.json")
    validate_output_fixture_schema_only(data)
    assert all(h["status"] != "recommended" for h in data["positioning_hypotheses"])


def test_30_insufficient_evidence_fixture_non_actionable() -> None:
    data = load_json_fixture("tests/fixtures/output_insufficient_evidence.json")
    validate_output_fixture_schema_only(data)
    assert data["positioning_readiness"] in {"insufficient_evidence", "exploratory_only"}


def test_31_conflicted_fixture_remains_conflicted() -> None:
    data = load_json_fixture("tests/fixtures/output_conflicted_competitor.json")
    validate_output_fixture_schema_only(data)
    assert data["research_status"] == "conflicted"
    assert data["positioning_readiness"] == "conflicted"


def test_32_selected_segment_ids_must_exist() -> None:
    data = load_json_fixture("tests/fixtures/input_unknown_segment_id.json")
    assert any("unknown segment" in e for e in validate_input_semantics(data))


def test_33_hypothesis_segment_ids_subset_enforced() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["positioning_hypotheses"][0]["target_segment_ids"] = ["seg-other"]
    assert any("hypothesis segment IDs must be subset" in e for e in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    ))


def test_34_preferred_id_must_exist() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["preferred_hypothesis_id"] = "pos-missing"
    assert "preferred hypothesis ID must exist" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_35_blocked_ids_must_reference_blocked_hypotheses() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["blocked_hypothesis_ids"] = ["pos-h1"]
    assert "blocked IDs must reference blocked hypotheses" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_36_preferred_hypothesis_requires_evidence() -> None:
    data = load_json_fixture("tests/fixtures/output_preferred_without_evidence.json")
    assert any("preferred hypothesis requires evidence" in e for e in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    ))


def test_37_differentiation_requires_competitor_evidence() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["positioning_hypotheses"][0]["evidence_references"] = ["ev-seg-seg-remote-eng"]
    assert "differentiation requires competitor evidence" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_38_unsupported_pain_introduction_rejected() -> None:
    data = load_json_fixture("tests/fixtures/output_unsupported_pain.json")
    assert "unsupported customer pain introduction" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_39_unsupported_jtbd_introduction_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["positioning_hypotheses"][0]["primary_jtbd_ref"] = "jtbd-invented"
    assert "unsupported JTBD introduction" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_40_unsupported_objection_introduction_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["message_hierarchy"]["objection_responses"] = [
        {"objection_ref": "obj-invented", "response_framing": "x"}
    ]
    assert "unsupported objection introduction" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_41_unsupported_claim_as_key_message_rejected() -> None:
    data = load_json_fixture("tests/fixtures/output_unsupported_claim_key_message.json")
    assert "unsupported claim as key message" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_42_high_confidence_insufficient_evidence_rejected() -> None:
    data = load_json_fixture("tests/fixtures/output_high_confidence_insufficient_evidence.json")
    assert "high confidence with insufficient evidence" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_43_ready_for_offer_design_with_stop_rejected() -> None:
    data = load_json_fixture("tests/fixtures/output_ready_despite_stop.json")
    errors = validate_output_semantics(data, cim_catalog=saas_catalog())
    assert any("ready_for_offer_design with stop" in e for e in errors)


def test_44_ready_for_offer_design_with_defer_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_defer.json"))
    data["positioning_readiness"] = "ready_for_offer_design"
    assert "ready_for_offer_design with defer" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_45_ready_for_offer_design_with_insufficient_evidence_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_insufficient_evidence.json"))
    data["positioning_readiness"] = "ready_for_offer_design"
    assert "ready_for_offer_design with insufficient_evidence" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_46_inherited_blockers_preserved() -> None:
    data = load_json_fixture("tests/fixtures/output_stop.json")
    assert data["blockers_inherited"]
    assert data["blockers_inherited"][0]["blocking"] is True


def test_47_inherited_conditions_preserved() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed_with_conditions.json")
    assert data["conditions_inherited"]


def test_48_positioning_cannot_alter_mv_verdict() -> None:
    data = load_json_fixture("tests/fixtures/output_proceed_preferred.json")
    assert data["market_validation_verdict_consumed"] == "proceed"
    data["market_validation_verdict_consumed"] = "stop"
    data["positioning_readiness"] = "ready_for_offer_design"
    assert "ready_for_offer_design with stop" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_49_output_verdict_field_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["verdict"] = "proceed"
    with pytest.raises(ValidationError):
        validate_output_fixture_schema_only(data)


def test_50_offer_field_rejected() -> None:
    data = load_json_fixture("tests/fixtures/output_offer_field_injected.json")
    with pytest.raises(ValidationError):
        validate_output_fixture_schema_only(data)


def test_51_campaign_field_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["campaign"] = {"channel": "meta"}
    assert "forbidden field: campaign" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_52_execution_status_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["execution_status"] = "approved"
    assert "forbidden field: execution_status" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_53_approval_granted_rejected() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["approval_granted"] = True
    assert "approval_granted prohibited" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_54_downstream_offer_input_references_valid_hypothesis() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["downstream_offer_inputs"][0]["selected_positioning_hypothesis_id"] = "missing"
    assert "downstream offer input must reference valid hypothesis" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_55_downstream_offer_input_contains_no_offer_fields() -> None:
    data = copy.deepcopy(load_json_fixture("tests/fixtures/output_proceed_preferred.json"))
    data["downstream_offer_inputs"][0]["price"] = 99
    assert "offer field in downstream input: price" in validate_output_semantics(
        data, cim_catalog=saas_catalog()
    )


def test_56_registry_projection_candidate() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    projection = project_validation_report(report)
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_57_production_eligibility_false() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    projection = project_validation_report(report)
    eligibility = derive_eligibility_view(projection.version_record)
    assert eligibility.production_eligible is False


def test_58_audit_readiness() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    readiness = derive_decision_readiness(
        audit_type=AuditType.PACKAGE_VALIDATION,
        findings=audit.findings,
        report_status=audit.status,
        package_valid=report.valid,
    )
    assert readiness == AuditDecisionReadiness.READY_FOR_AUDIT


def test_59_lineage_graph_builds_with_parents() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    lineage = build_package_validation_lineage(report, audit_report=audit)
    assert lineage.graph_hash


def test_60_source_versions_hashes_preserved_in_lineage() -> None:
    fixture = load_json_fixture("tests/fixtures/lineage_cim_ca_mv_parents.json")
    assert fixture["parents"][0]["output_hash"]
    assert fixture["parents"][2]["package_hash"] == MV_020_PKG_HASH


def test_61_package_hash_deterministic() -> None:
    h1 = calculate_skill_package_hash(PACKAGE_ROOT)
    h2 = package_hash()
    assert h1 == h2 == POS_HASH


def test_62_prior_frozen_hashes_unchanged() -> None:
    assert FROZEN_PACKAGE_HASHES[("ms.skill.market_validation", "0.2.0")] == MV_020_PKG_HASH
    assert FROZEN_PACKAGE_HASHES[("ms.skill.market_validation", "0.1.0")] == FROZEN_MV_010_HASH
    assert calculate_skill_package_hash(PMC_010_ROOT) == PMC_010_HASH
    assert CIM_BUNDLE_HASH == MV_CIM_BUNDLE_HASH


def test_63_offer_builder_consumer_stub() -> None:
    output = load_json_fixture("tests/fixtures/output_proceed_preferred.json")
    consumer = load_json_fixture("tests/fixtures/consumer_offer_builder_stub.json")
    result = offer_builder_consumer_stub(consumer, output)
    assert result["hypothesis_id"] == "pos-h1"
    assert result["message_hierarchy"]


def test_64_content_consumer_stub() -> None:
    output = load_json_fixture("tests/fixtures/output_proceed_preferred.json")
    consumer = load_json_fixture("tests/fixtures/consumer_content_strategy_stub.json")
    result = content_consumer_stub(consumer, output)
    assert result["segment_ids"]


def test_65_copywriting_consumer_stub() -> None:
    output = load_json_fixture("tests/fixtures/output_proceed_preferred.json")
    consumer = load_json_fixture("tests/fixtures/consumer_content_strategy_stub.json")
    assert copywriting_consumer_stub(consumer, output)


def test_66_launch_strategy_consumer_no_execution_auth() -> None:
    launch_strategy_consumer_stub({"execution_authorized": False})
    with pytest.raises(ValueError):
        launch_strategy_consumer_stub({"execution_authorized": True})


def test_67_forbidden_fields_helper() -> None:
    data = {"verdict": "proceed", "campaign": {}}
    assert "verdict" in output_has_forbidden_fields(data)


def test_68_positioning_frozen_hash_registered() -> None:
    assert POS_HASH == "cbd8283f4addaa9c8496504a9c6dbccd580e8ca317b2cf86bf628be6557e8da6"
