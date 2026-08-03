"""Test helpers for SKILL-02.5 CIM shared schema freeze."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.knowledge.cim_compatibility import (
    FORBIDDEN_RECOMPUTE_FIELDS,
    normalize_icp_local_cim,
    validate_icp_local_against_shared,
)
from app.knowledge.cim_hashing import (
    compute_bundle_hash,
    compute_file_hashes,
    semantic_manifest_hash,
)
from app.knowledge.cim_schema_registry import (
    CANONICAL_URI_BASE,
    SCHEMA_FILES,
    SUPPORTED_VERSIONS,
    build_registry,
    bundle_root,
    canonical_uri,
    schema_validator,
    validate_canonical_document,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_ROOT = REPO_ROOT / "packages/knowledge/customer_intelligence/0.1.0"
CONSUMERS_ROOT = SHARED_ROOT / "consumers"
ICP_ROOT = REPO_ROOT / "packages/skills/ms.skill.icp_segmentation"
FREEZE_MANIFEST_PATH = SHARED_ROOT / "freeze_manifest.json"

FROZEN_ICP_HASH = "075a4f1989a9050614babec004dda54a420d7f7bd717d9ac7e8a34b41e8ae71a"
FROZEN_BUNDLE_HASH = "b13cc76eb8f6405d114a457a8a4bf12a4a5330d9a37bd0adcfd93f48353421ea"

MKG_ENTITY_MAPPINGS = {
    "CustomerIntelligenceDocument": "customer_intelligence",
    "CustomerSegment": "segment",
    "JobToBeDone": "job",
    "PainPoint": "pain",
    "DesiredOutcome": "outcome",
    "BuyingTrigger": "trigger",
    "BuyingBarrier": "barrier",
    "Objection": "objection",
    "DecisionRole": "decision_role",
    "TrustDriver": "trust_driver",
    "EvidenceReference": "evidence",
    "CompetitorRelationship": "competitor_relationship",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_freeze_manifest() -> dict[str, Any]:
    return load_json(FREEZE_MANIFEST_PATH)


def load_icp_cim_fixture(name: str = "output_complete_saas.json") -> dict[str, Any]:
    output = load_json(ICP_ROOT / "tests/fixtures" / name)
    return output["customer_intelligence"]


def load_consumer_fixture(name: str) -> dict[str, Any]:
    return load_json(CONSUMERS_ROOT / name)


def _load_cim_schema() -> dict[str, Any]:
    path = SHARED_ROOT / "customer-intelligence.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_shared_cim(data: dict[str, Any]) -> None:
    validate_canonical_document("0.1.0", "customer-intelligence.schema.json", data)


def validate_shared_segment(data: dict[str, Any]) -> None:
    validate_canonical_document("0.1.0", "customer-segment.schema.json", data)


def validate_shared_claim(data: dict[str, Any]) -> None:
    validate_canonical_document("0.1.0", "customer-claim.schema.json", data)


def validate_shared_jtbd(data: dict[str, Any]) -> None:
    validate_canonical_document("0.1.0", "job-to-be-done.schema.json", data)


def validate_shared_decision_role(data: dict[str, Any]) -> None:
    validate_canonical_document("0.1.0", "decision-role.schema.json", data)


def validate_shared_priority(data: dict[str, Any]) -> None:
    validate_canonical_document("0.1.0", "priority-assessment.schema.json", data)


def validate_shared_conflict(data: dict[str, Any]) -> None:
    validate_canonical_document("0.1.0", "segment-conflict.schema.json", data)


def validate_shared_provenance(data: dict[str, Any]) -> None:
    validate_canonical_document("0.1.0", "provenance.schema.json", data)


def positioning_reads_cim_without_recompute(
    consumer: dict[str, Any], cim: dict[str, Any]
) -> dict[str, Any]:
    segment_by_id = {s["segment_id"]: s for s in cim["segments"]}
    seg = segment_by_id[consumer["selected_segment_ids"][0]]
    return {
        "jtbd": seg.get("jobs_to_be_done", []),
        "pains": seg.get("pain_points", []),
        "objections": seg.get("objections", []),
        "trust_drivers": seg.get("trust_drivers", []),
        "recomputed_fields": consumer.get("redefined_fields", []),
    }


__all__ = [
    "CANONICAL_URI_BASE",
    "CONSUMERS_ROOT",
    "FORBIDDEN_RECOMPUTE_FIELDS",
    "FROZEN_BUNDLE_HASH",
    "FROZEN_ICP_HASH",
    "MKG_ENTITY_MAPPINGS",
    "SCHEMA_FILES",
    "SHARED_ROOT",
    "SUPPORTED_VERSIONS",
    "build_registry",
    "bundle_root",
    "canonical_uri",
    "compute_bundle_hash",
    "compute_file_hashes",
    "_load_cim_schema",
    "load_consumer_fixture",
    "load_freeze_manifest",
    "load_icp_cim_fixture",
    "normalize_icp_local_cim",
    "positioning_reads_cim_without_recompute",
    "schema_validator",
    "semantic_manifest_hash",
    "validate_icp_local_against_shared",
    "validate_shared_cim",
    "validate_shared_claim",
    "validate_shared_conflict",
    "validate_shared_decision_role",
    "validate_shared_jtbd",
    "validate_shared_priority",
    "validate_shared_provenance",
    "validate_shared_segment",
]
