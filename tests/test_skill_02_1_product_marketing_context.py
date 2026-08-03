"""SKILL-02.1 — Product Marketing Context native package tests."""

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
from app.schemas.contracts import SkillContextReadiness, SkillLifecycleStatus
from app.skills.hashing import calculate_skill_package_hash
from app.skills.package_validator import validate_skill_package
from app.skills.registry_projection import project_validation_report
from app.skills.registry_queries import derive_eligibility_view
from jsonschema.exceptions import ValidationError
from pydantic import ValidationError as PydanticValidationError
from tests.support.product_marketing_context_validation import (
    FROZEN_MARKET_VALIDATION_HASH,
    FROZEN_MARKET_VALIDATION_ROOT,
    PACKAGE_ROOT,
    SKILL_01_0_ALLOWED_STATUSES,
    load_json_fixture,
    manifest_contains_required_keys,
    no_secrets_in_manifest,
    output_has_verdict_field,
    package_paths_safe,
    package_structure_valid,
    parse_manifest_scalar,
    read_manifest_text,
    validate_claim_schema,
    validate_input_schema,
    validate_output_fixture,
    validate_output_schema,
)

MANIFEST = read_manifest_text()
PACKAGE_HASH: str | None = None


def _package_hash() -> str:
    global PACKAGE_HASH
    if PACKAGE_HASH is None:
        PACKAGE_HASH = calculate_skill_package_hash(PACKAGE_ROOT)
    return PACKAGE_HASH


def test_01_package_validates_through_production_validator() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    assert report.valid is True
    assert report.skill_id == "ms.skill.product_marketing_context"
    assert report.status == SkillLifecycleStatus.CANDIDATE


def test_02_status_is_candidate() -> None:
    assert parse_manifest_scalar(MANIFEST, "status") == "candidate"
    assert parse_manifest_scalar(MANIFEST, "status") in SKILL_01_0_ALLOWED_STATUSES


def test_03_no_tools_in_manifest() -> None:
    assert "allowed_tools: []" in MANIFEST


def test_04_network_denied() -> None:
    assert "network_policy:" in MANIFEST
    assert "default: deny" in MANIFEST


def test_05_scripts_disabled() -> None:
    assert "script_policy:" in MANIFEST
    assert "enabled: false" in MANIFEST


def test_06_input_schema_draft_2020_12_valid() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    input_result = next(
        r for r in report.schema_results if r.schema_ref == "schemas/input.schema.json"
    )
    assert input_result.valid is True
    assert input_result.draft == "https://json-schema.org/draft/2020-12/schema"


def test_07_output_schema_draft_2020_12_valid() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    output_result = next(
        r for r in report.schema_results if r.schema_ref == "schemas/output.schema.json"
    )
    assert output_result.valid is True
    assert output_result.draft == "https://json-schema.org/draft/2020-12/schema"


def test_08_complete_input_validates() -> None:
    data = load_json_fixture("tests/fixtures/input_complete_saas.json")
    validate_input_schema(data)


def test_09_partial_input_validates() -> None:
    data = load_json_fixture("tests/fixtures/input_incomplete_cafe.json")
    validate_input_schema(data)


def test_10_conflicted_input_validates() -> None:
    data = load_json_fixture("tests/fixtures/input_conflicted_pricing.json")
    validate_input_schema(data)


def test_11_invalid_source_type_rejected() -> None:
    claim = {
        "claim_id": "bad-src",
        "domain": "pricing",
        "statement": "Invalid source type",
        "source_type": "fabricated_source",
        "verification_status": "unverified",
        "confidence": "low",
    }
    with pytest.raises(ValidationError):
        validate_claim_schema(claim)


def test_12_invalid_verification_status_rejected() -> None:
    claim = {
        "claim_id": "bad-ver",
        "domain": "pricing",
        "statement": "Invalid verification",
        "source_type": "user_statement",
        "verification_status": "confirmed",
        "confidence": "low",
    }
    with pytest.raises(ValidationError):
        validate_claim_schema(claim)


def test_13_verified_claim_without_source_rejected() -> None:
    data = load_json_fixture("tests/fixtures/input_invalid_verified_no_source.json")
    with pytest.raises(ValidationError):
        validate_input_schema(data)


def test_14_assumption_is_not_evidence() -> None:
    output = load_json_fixture("tests/fixtures/output_complete_ready.json")
    parsed = validate_output_fixture(output)
    assumption_ids = {item["claim_id"] for item in parsed.assumptions}
    evidence_claims = {item.get("claim_id") for item in parsed.evidence_inventory}
    assert assumption_ids.isdisjoint(evidence_claims)


def test_15_inference_not_verified_by_default() -> None:
    inference_claim = {
        "claim_id": "inf-001",
        "domain": "customer_segment",
        "statement": "Inferred segment from partial data",
        "source_type": "system_inference",
        "verification_status": "verified",
        "confidence": "medium",
        "inference": True,
        "source_reference": "should-not-allow",
    }
    with pytest.raises(ValidationError):
        validate_claim_schema(inference_claim)


def test_16_contradicted_claim_preserved_in_output() -> None:
    output = load_json_fixture("tests/fixtures/output_conflicted.json")
    parsed = validate_output_fixture(output)
    assert parsed.conflicts
    assert len(parsed.normalized_pricing_claims) == 2


def test_17_complete_context_output_validates() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_ready.json")
    parsed = validate_output_fixture(data)
    assert parsed.readiness == SkillContextReadiness.READY


def test_18_partial_readiness_output_validates() -> None:
    data = load_json_fixture("tests/fixtures/output_partially_ready.json")
    parsed = validate_output_fixture(data)
    assert parsed.readiness == SkillContextReadiness.PARTIALLY_READY


def test_19_conflict_output_validates() -> None:
    data = load_json_fixture("tests/fixtures/output_conflicted.json")
    parsed = validate_output_fixture(data)
    assert parsed.readiness == SkillContextReadiness.CONFLICTED


def test_20_unknown_readiness_rejected() -> None:
    data = load_json_fixture("tests/fixtures/output_invalid_readiness_enum.json")
    with pytest.raises(ValidationError):
        validate_output_schema(data)


def test_21_output_contains_skill_id_and_version() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_ready.json")
    parsed = validate_output_fixture(data)
    assert parsed.skill_id == "ms.skill.product_marketing_context"
    assert parsed.skill_version == "0.1.0"


def test_22_output_contains_provenance() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_ready.json")
    parsed = validate_output_fixture(data)
    assert parsed.provenance.skill_id == "ms.skill.product_marketing_context"


def test_23_output_contains_input_and_output_hashes() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_ready.json")
    parsed = validate_output_fixture(data)
    assert len(parsed.input_hash) == 64
    assert len(parsed.output_hash) == 64


def test_24_no_viability_verdict_field_exists() -> None:
    for fixture in (
        "tests/fixtures/output_complete_ready.json",
        "tests/fixtures/output_partially_ready.json",
        "tests/fixtures/output_conflicted.json",
    ):
        data = load_json_fixture(fixture)
        assert not output_has_verdict_field(data)
    output_schema = json.loads((PACKAGE_ROOT / "schemas/output.schema.json").read_text())
    assert "verdict" not in output_schema.get("properties", {})


def test_25_no_connector_or_tool_permission_in_manifest() -> None:
    assert "allowed_tools: []" in MANIFEST
    assert parse_manifest_scalar(MANIFEST, "source") == "platform_native"


def test_26_registry_projection_remains_candidate() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    projection = project_validation_report(report)
    assert projection.version_record is not None
    assert projection.version_record.lifecycle_status == SkillLifecycleStatus.CANDIDATE


def test_27_production_eligibility_false() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    projection = project_validation_report(report)
    assert projection.version_record is not None
    eligibility = derive_eligibility_view(projection.version_record)
    assert eligibility.production_eligible is False
    assert "candidate_not_production_eligible" in eligibility.blockers


def test_28_audit_report_ready_for_audit_not_activation_ready() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    readiness = derive_decision_readiness(
        audit_type=AuditType.PACKAGE_VALIDATION,
        findings=audit.findings,
        report_status=audit.status,
        package_valid=report.valid,
    )
    assert readiness == AuditDecisionReadiness.READY_FOR_AUDIT
    assert readiness != AuditDecisionReadiness.READY_FOR_HUMAN_REVIEW


def test_29_lineage_graph_builds_in_memory() -> None:
    report = validate_skill_package(PACKAGE_ROOT)
    audit = adapt_package_validation_report(report)
    graph = build_package_validation_lineage(report, audit_report=audit)
    assert graph.graph_hash
    assert len(graph.nodes) >= 2


def test_30_frozen_market_validation_package_unchanged() -> None:
    frozen_hash = calculate_skill_package_hash(FROZEN_MARKET_VALIDATION_ROOT)
    assert frozen_hash == FROZEN_MARKET_VALIDATION_HASH
    frozen_report = validate_skill_package(FROZEN_MARKET_VALIDATION_ROOT)
    assert frozen_report.valid is True


def test_package_structure_and_manifest_keys() -> None:
    assert package_structure_valid()
    assert manifest_contains_required_keys(MANIFEST) == []


def test_no_secrets_and_paths_safe() -> None:
    assert no_secrets_in_manifest(MANIFEST)
    assert package_paths_safe()


def test_skill_md_instruction_only() -> None:
    skill_md = (PACKAGE_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "Readiness rules" in skill_md
    assert "api_key" not in skill_md.lower()
    assert "allowed_tools" not in skill_md


def test_package_hash_deterministic() -> None:
    h1 = _package_hash()
    h2 = calculate_skill_package_hash(PACKAGE_ROOT)
    assert h1 == h2


def test_cross_package_dependency_fields_preserved() -> None:
    """PMC output preserves fields required for future downstream dependency consumption."""
    output = load_json_fixture("tests/fixtures/output_complete_ready.json")
    parsed = validate_output_fixture(output)
    assert parsed.skill_id
    assert parsed.skill_version
    assert parsed.output_hash
    assert parsed.assumptions
    assert parsed.unknowns == []
    assert parsed.conflicts == []
    assert parsed.evidence_inventory
    assert parsed.provenance.skill_id == parsed.skill_id


def test_prior_skill_output_input_validates() -> None:
    data = load_json_fixture("tests/fixtures/input_prior_skill_output.json")
    validate_input_schema(data)


def test_invalid_output_missing_provenance_rejected() -> None:
    data = load_json_fixture("tests/fixtures/output_invalid_missing_provenance.json")
    with pytest.raises(ValidationError):
        validate_output_schema(data)


def test_unknown_audience_input_validates() -> None:
    data = load_json_fixture("tests/fixtures/input_unknown_audience.json")
    validate_input_schema(data)


def test_output_fixture_extra_fields_rejected() -> None:
    data = load_json_fixture("tests/fixtures/output_complete_ready.json")
    data["verdict"] = "proceed"
    with pytest.raises((ValidationError, PydanticValidationError)):
        validate_output_fixture(data)
