"""CIM compatibility mapping and checks between local ICP and shared contracts."""

from __future__ import annotations

import copy
import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from app.knowledge.cim_schema_registry import (
    SUPPORTED_VERSIONS,
    validate_canonical_document,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MAPPING_PATH = (
    _REPO_ROOT
    / "packages/knowledge/customer_intelligence/0.1.0/icp-local-compatibility.json"
)

FORBIDDEN_RECOMPUTE_FIELDS = frozenset(
    {
        "jobs_to_be_done",
        "pain_points",
        "desired_outcomes",
        "buying_triggers",
        "buying_barriers",
        "objections",
        "decision_roles",
        "trust_drivers",
        "awareness_stage",
        "market_sophistication",
        "inclusion_criteria",
        "exclusion_criteria",
    }
)


class CompatibilityStatus(StrEnum):
    COMPATIBLE = "compatible"
    CONDITIONALLY_COMPATIBLE = "conditionally_compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


def load_icp_local_mapping() -> dict[str, Any]:
    return json.loads(_MAPPING_PATH.read_text(encoding="utf-8"))


def normalize_icp_local_cim(document: dict[str, Any]) -> dict[str, Any]:
    """Map frozen ICP 0.1.0 local CIM (0.1.0-draft) to shared CIM 0.1.0."""
    normalized = copy.deepcopy(document)
    mapping = load_icp_local_mapping()
    version_map = mapping["field_mappings"]["cim_version"]
    if normalized.get("cim_version") == version_map["local"]:
        normalized["cim_version"] = version_map["shared"]
    return normalized


def validate_icp_local_against_shared(document: dict[str, Any]) -> None:
    normalized = normalize_icp_local_cim(document)
    validate_canonical_document("0.1.0", "customer-intelligence.schema.json", normalized)


def assess_version_compatibility(source_version: str, target_version: str) -> CompatibilityStatus:
    if source_version == target_version:
        return CompatibilityStatus.COMPATIBLE
    if source_version not in SUPPORTED_VERSIONS or target_version not in SUPPORTED_VERSIONS:
        return CompatibilityStatus.UNKNOWN
    return CompatibilityStatus.INCOMPATIBLE


def assess_schema_change(
    *,
    removed_required_fields: list[str] | None = None,
    narrowed_enums: list[str] | None = None,
    semantic_reuse: list[str] | None = None,
) -> CompatibilityStatus:
    if semantic_reuse:
        return CompatibilityStatus.INCOMPATIBLE
    if removed_required_fields or narrowed_enums:
        return CompatibilityStatus.INCOMPATIBLE
    return CompatibilityStatus.COMPATIBLE


def consumer_redefines_forbidden_fields(payload: dict[str, Any]) -> list[str]:
    forbidden = payload.get("redefined_fields", [])
    return [field for field in FORBIDDEN_RECOMPUTE_FIELDS if field in forbidden]


def consumer_missing_cim_reference(payload: dict[str, Any]) -> bool:
    required = ("cim_schema_uri", "cim_version", "cim_document_hash", "source_skill_id")
    return any(key not in payload for key in required)


__all__ = [
    "CompatibilityStatus",
    "FORBIDDEN_RECOMPUTE_FIELDS",
    "assess_schema_change",
    "assess_version_compatibility",
    "consumer_missing_cim_reference",
    "consumer_redefines_forbidden_fields",
    "load_icp_local_mapping",
    "normalize_icp_local_cim",
    "validate_icp_local_against_shared",
]
