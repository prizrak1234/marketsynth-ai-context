"""SKILL-02.5 — CIM shared schema freeze tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from app.knowledge.cim_compatibility import (
    CompatibilityStatus,
    assess_schema_change,
    assess_version_compatibility,
    consumer_redefines_forbidden_fields,
    load_icp_local_mapping,
    normalize_icp_local_cim,
)
from app.knowledge.cim_hashing import (
    compute_bundle_hash,
    compute_file_hashes,
    semantic_manifest_hash,
    semantic_manifest_subset,
)
from app.knowledge.cim_schema_registry import (
    UnknownCanonicalUriError,
    UnknownCimSchemaVersionError,
    bundle_root,
    canonical_uri,
    resolve_canonical_uri,
)
from app.skills.hashing import calculate_skill_package_hash
from app.skills.legacy_output_contract import FROZEN_PACKAGE_HASHES
from jsonschema.exceptions import ValidationError
from tests.support.cim_shared_schema_validation import (
    CONSUMERS_ROOT,
    FROZEN_BUNDLE_HASH,
    FROZEN_ICP_HASH,
    MKG_ENTITY_MAPPINGS,
    SCHEMA_FILES,
    SHARED_ROOT,
    SUPPORTED_VERSIONS,
    _load_cim_schema,
    load_consumer_fixture,
    load_freeze_manifest,
    load_icp_cim_fixture,
    positioning_reads_cim_without_recompute,
    validate_icp_local_against_shared,
    validate_shared_cim,
    validate_shared_claim,
    validate_shared_conflict,
    validate_shared_decision_role,
    validate_shared_jtbd,
    validate_shared_priority,
    validate_shared_provenance,
    validate_shared_segment,
)
from tests.support.competitor_analysis_validation import PACKAGE_ROOT as CA_ROOT
from tests.support.icp_segmentation_validation import (
    FROZEN_CA_HASH,
    FROZEN_PMC_020_HASH,
    MR_ROOT,
    PMC_020_ROOT,
)
from tests.support.icp_segmentation_validation import (
    PACKAGE_ROOT as ICP_ROOT,
)
from tests.support.product_marketing_context_validation import (
    FROZEN_MARKET_VALIDATION_ROOT,
)
from tests.support.product_marketing_context_validation import (
    PACKAGE_ROOT as PMC_010_ROOT,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_01_shared_schema_bundle_exists() -> None:
    assert bundle_root("0.1.0").is_dir()
    for name in SCHEMA_FILES:
        assert (SHARED_ROOT / name).is_file()


def test_02_canonical_base_uri_versioned() -> None:
    manifest = load_freeze_manifest()
    assert manifest["canonical_uri_base"] == "https://schemas.marketsynth.ai/customer-intelligence/0.1.0/"
    assert manifest["schema_version"] == "0.1.0"


def test_03_no_unversioned_latest_uri() -> None:
    latest = "https://schemas.marketsynth.ai/customer-intelligence/customer-intelligence.schema.json"
    with pytest.raises(UnknownCanonicalUriError):
        resolve_canonical_uri(latest)


def test_04_no_network_resolution_for_unknown_host() -> None:
    with pytest.raises(UnknownCanonicalUriError):
        resolve_canonical_uri("https://example.com/customer-intelligence/0.1.0/customer-intelligence.schema.json")


def test_05_unknown_schema_uri_rejected() -> None:
    with pytest.raises(UnknownCanonicalUriError):
        resolve_canonical_uri(
            "https://schemas.marketsynth.ai/customer-intelligence/9.9.9/customer-intelligence.schema.json"
        )


def test_06_duplicate_schema_id_rejected() -> None:
    seen: set[str] = set()
    for name in SCHEMA_FILES:
        schema = json.loads((SHARED_ROOT / name).read_text(encoding="utf-8"))
        schema_id = schema["$id"]
        assert schema_id not in seen
        seen.add(schema_id)


def test_07_shared_cim_schema_validates() -> None:
    cim = normalize_icp_local_cim(load_icp_cim_fixture())
    validate_shared_cim(cim)


def test_08_shared_segment_schema_validates() -> None:
    cim = normalize_icp_local_cim(load_icp_cim_fixture())
    validate_shared_segment(cim["segments"][0])


def test_09_shared_claim_schema_validates() -> None:
    cim = normalize_icp_local_cim(load_icp_cim_fixture())
    validate_shared_claim(cim["segments"][0]["pain_points"][0])


def test_10_shared_jtbd_schema_validates() -> None:
    cim = normalize_icp_local_cim(load_icp_cim_fixture())
    validate_shared_jtbd(cim["segments"][0]["jobs_to_be_done"][0])


def test_11_shared_decision_role_schema_validates() -> None:
    cim = normalize_icp_local_cim(load_icp_cim_fixture())
    validate_shared_decision_role(cim["segments"][0]["decision_roles"][0])


def test_12_shared_priority_schema_validates() -> None:
    cim = normalize_icp_local_cim(load_icp_cim_fixture())
    validate_shared_priority(cim["segments"][0]["priority_assessment"])


def test_13_shared_conflict_schema_validates() -> None:
    fixture_path = ICP_ROOT / "tests/fixtures/output_conflicted_interviews.json"
    output = json.loads(fixture_path.read_text(encoding="utf-8"))
    cim = normalize_icp_local_cim(output["customer_intelligence"])
    validate_shared_conflict(cim["segment_conflicts"][0])


def test_14_shared_provenance_schema_validates() -> None:
    validate_shared_provenance(
        {
            "source_skill_id": "ms.skill.icp_segmentation",
            "source_skill_version": "0.1.0",
            "source_reference": "fixture-segment-provenance",
        }
    )


def test_15_icp_valid_fixture_validates_against_shared_schema() -> None:
    validate_icp_local_against_shared(load_icp_cim_fixture())


def test_16_invalid_icp_fixture_still_rejected() -> None:
    cim = normalize_icp_local_cim(load_icp_cim_fixture())
    bad = copy.deepcopy(cim)
    bad["verdict"] = "proceed"
    with pytest.raises(ValidationError):
        validate_shared_cim(bad)


def test_17_icp_frozen_hash_unchanged() -> None:
    assert calculate_skill_package_hash(ICP_ROOT) == FROZEN_ICP_HASH


def test_18_compatibility_mapping_preserves_local_to_shared_identity() -> None:
    mapping = load_icp_local_mapping()
    local = load_icp_cim_fixture()
    normalized = normalize_icp_local_cim(local)
    assert local["cim_version"] == mapping["field_mappings"]["cim_version"]["local"]
    assert normalized["cim_version"] == mapping["field_mappings"]["cim_version"]["shared"]
    assert local["cim_id"] == normalized["cim_id"]
    assert local["segments"][0]["segment_id"] == normalized["segments"][0]["segment_id"]


def test_19_positioning_consumer_fixture_validates() -> None:
    fixture = load_consumer_fixture("positioning_consumer.json")
    assert fixture["consumer_skill_id"] == "ms.skill.positioning"
    assert fixture["cim_schema_uri"].endswith("customer-intelligence.schema.json")


def test_20_offer_builder_consumer_fixture_validates() -> None:
    fixture = load_consumer_fixture("offer_builder_consumer.json")
    assert fixture["consumer_skill_id"] == "ms.skill.offer_builder"


def test_21_content_consumer_fixture_validates() -> None:
    fixture = load_consumer_fixture("content_strategy_consumer.json")
    assert "selected_segment_ids" in fixture


def test_22_copywriting_consumer_fixture_validates() -> None:
    fixture = load_consumer_fixture("copywriting_consumer.json")
    assert fixture["consumer_skill_id"] == "ms.skill.copywriting"


def test_23_crm_consumer_fixture_validates() -> None:
    fixture = load_consumer_fixture("crm_handoff_consumer.json")
    assert fixture["consumer_output"]["personal_records"] == []


def test_24_advertising_planning_consumer_fixture_validates() -> None:
    fixture = load_consumer_fixture("advertising_planning_consumer.json")
    assert fixture["consumer_output"]["audience_plan"]["segment_ids"]


def test_25_market_validation_consumer_fixture_validates() -> None:
    fixture = load_consumer_fixture("market_validation_consumer.json")
    assert fixture["consumer_skill_version"] == "0.2.0"


def test_26_positioning_consumer_does_not_redefine_jtbd() -> None:
    fixture = load_consumer_fixture("positioning_consumer.json")
    assert "jobs_to_be_done" in fixture["forbidden_recompute_fields"]
    assert consumer_redefines_forbidden_fields(fixture) == []


def test_27_positioning_consumer_does_not_redefine_pains() -> None:
    fixture = load_consumer_fixture("positioning_consumer.json")
    assert "pain_points" in fixture["forbidden_recompute_fields"]


def test_28_offer_consumer_does_not_redefine_objections() -> None:
    fixture = load_consumer_fixture("offer_builder_consumer.json")
    assert "objections" in fixture["forbidden_recompute_fields"]
    assert consumer_redefines_forbidden_fields(fixture) == []


def test_29_content_consumer_references_selected_segment_ids() -> None:
    fixture = load_consumer_fixture("content_strategy_consumer.json")
    assert fixture["selected_segment_ids"]


def test_30_crm_consumer_contains_no_personal_customer_records() -> None:
    fixture = load_consumer_fixture("crm_handoff_consumer.json")
    assert fixture["consumer_output"]["personal_records"] == []


def test_31_shared_cim_has_no_viability_verdict() -> None:
    schema = _load_cim_schema()
    assert "verdict" not in schema.get("properties", {})


def test_32_shared_cim_has_no_positioning_field() -> None:
    schema = _load_cim_schema()
    assert "positioning" not in schema.get("properties", {})


def test_33_shared_cim_has_no_offer_field() -> None:
    schema = _load_cim_schema()
    assert "final_offer" not in schema.get("properties", {})


def test_34_shared_cim_has_no_execution_status() -> None:
    schema = _load_cim_schema()
    assert "execution_status" not in schema.get("properties", {})


def test_35_schema_file_hashes_deterministic() -> None:
    manifest = load_freeze_manifest()
    assert compute_file_hashes("0.1.0") == manifest["file_hashes"]


def test_36_bundle_hash_deterministic() -> None:
    manifest = load_freeze_manifest()
    computed = compute_bundle_hash(manifest["file_hashes"])
    assert computed == FROZEN_BUNDLE_HASH == manifest["bundle_hash"]


def test_37_timestamp_excluded_from_semantic_bundle_hash() -> None:
    manifest = load_freeze_manifest()
    h1 = semantic_manifest_hash(manifest)
    mutated = copy.deepcopy(manifest)
    mutated["generated_at"] = "2099-01-01T00:00:00Z"
    h2 = semantic_manifest_hash(mutated)
    assert h1 == h2


def test_38_freeze_manifest_semantic_subset_deterministic() -> None:
    manifest = load_freeze_manifest()
    subset = semantic_manifest_subset(manifest)
    assert subset["schema_version"] == "0.1.0"
    assert "generated_at" not in subset


def test_39_unknown_future_version_rejected() -> None:
    with pytest.raises(UnknownCimSchemaVersionError):
        bundle_root("99.0.0")


def test_40_compatible_additive_schema_fixture_accepted() -> None:
    status = assess_schema_change()
    assert status == CompatibilityStatus.COMPATIBLE


def test_41_removed_required_field_marked_incompatible() -> None:
    status = assess_schema_change(removed_required_fields=["cim_id"])
    assert status == CompatibilityStatus.INCOMPATIBLE


def test_42_narrowed_enum_marked_incompatible() -> None:
    status = assess_schema_change(narrowed_enums=["readiness"])
    assert status == CompatibilityStatus.INCOMPATIBLE


def test_43_changed_field_meaning_not_auto_compatible() -> None:
    status = assess_schema_change(semantic_reuse=["pain_points"])
    assert status == CompatibilityStatus.INCOMPATIBLE


def test_44_mkg_mapping_document_exists() -> None:
    doc = REPO_ROOT / "docs/knowledge/CIM-MKG-mapping-v0.1.0.md"
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "CustomerIntelligenceDocument" in text
    assert len(MKG_ENTITY_MAPPINGS) >= 10


def test_45_no_graph_db_dependency_introduced() -> None:
    assert not (REPO_ROOT / "app/knowledge/graph_db.py").exists()


def test_46_no_persistence_introduced() -> None:
    assert not (REPO_ROOT / "app/db/models/customer_intelligence.py").exists()


def test_47_legacy_frozen_package_hashes_unchanged() -> None:
    pmc = calculate_skill_package_hash(PMC_010_ROOT)
    mv = calculate_skill_package_hash(FROZEN_MARKET_VALIDATION_ROOT)
    mr = calculate_skill_package_hash(MR_ROOT)
    ca = calculate_skill_package_hash(CA_ROOT)
    icp = calculate_skill_package_hash(ICP_ROOT)
    pmc020 = calculate_skill_package_hash(PMC_020_ROOT)
    assert pmc == FROZEN_PACKAGE_HASHES[("ms.skill.product_marketing_context", "0.1.0")]
    assert mv == FROZEN_PACKAGE_HASHES[("ms.skill.market_validation", "0.1.0")]
    assert mr == "6acce32a4952de75d97129d8d39cc15c14a97805fc8850927bac3c19cc6fc14e"
    assert ca == FROZEN_CA_HASH
    assert icp == FROZEN_ICP_HASH
    assert pmc020 == FROZEN_PMC_020_HASH


def test_48_positioning_consumer_reads_cim_without_rederivation() -> None:
    cim = load_icp_cim_fixture()
    consumer = load_consumer_fixture("positioning_consumer.json")
    consumed = positioning_reads_cim_without_recompute(consumer, cim)
    assert consumed["jtbd"]
    assert consumed["pains"]
    assert consumed["recomputed_fields"] == []


def test_supported_versions_explicit() -> None:
    assert "0.1.0" in SUPPORTED_VERSIONS
    assert assess_version_compatibility("0.1.0", "0.1.0") == CompatibilityStatus.COMPATIBLE


def test_canonical_uri_helper() -> None:
    uri = canonical_uri("0.1.0", "customer-intelligence.schema.json")
    assert uri.startswith("https://schemas.marketsynth.ai/customer-intelligence/0.1.0/")


def test_consumer_fixtures_directory_complete() -> None:
    expected = {
        "positioning_consumer.json",
        "offer_builder_consumer.json",
        "content_strategy_consumer.json",
        "copywriting_consumer.json",
        "crm_handoff_consumer.json",
        "advertising_planning_consumer.json",
        "market_validation_consumer.json",
    }
    assert expected.issubset({p.name for p in CONSUMERS_ROOT.glob("*.json")})
