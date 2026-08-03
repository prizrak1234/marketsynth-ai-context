"""Pilot pattern bundle serialization — read-only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
WPL_ROOT = REPO_ROOT / "packages" / "knowledge" / "workflow_patterns" / "0.1.0"
PILOT_DIR = WPL_ROOT / "patterns" / "pilot"
PRACTICE_DIR = WPL_ROOT / "practices" / "pilot"
PILOT_INDEX = WPL_ROOT / "pilot_index.json"
PILOT_MANIFEST = WPL_ROOT / "pilot_freeze_manifest.json"
PILOT_AUDITS = WPL_ROOT / "pilot_audit_records.json"
PILOT_PRACTICE_INDEX = WPL_ROOT / "pilot_practice_index.json"
PILOT_SOURCE_SUPPORT_MAP = WPL_ROOT / "pilot_source_support_map.json"
CORE_DIR = WPL_ROOT / "patterns" / "core"
CORE_PRACTICE_DIR = WPL_ROOT / "practices" / "core"
CORE_INDEX = WPL_ROOT / "core_index.json"
CORE_MANIFEST = WPL_ROOT / "core_freeze_manifest.json"
CORE_AUDITS = WPL_ROOT / "core_audit_records.json"
CORE_PRACTICE_INDEX = WPL_ROOT / "core_practice_index.json"
CORE_SOURCE_SUPPORT_MAP = WPL_ROOT / "core_source_support_map.json"

FROZEN_PILOT_BUNDLE_HASH = "d2c3f64171bae91fe84708146ab05ff3fde3941f7645abcb006ca9de74a1a284"
FROZEN_CORE_BUNDLE_HASH = "b715466982b73f86c11bb05310d72def00a540982baea6ab80882e06b0737fbf"
FROZEN_CATALOG_HASH = "5389c3a7fe77a8625e4cceab76da79ee33b816437a671d05a1dac969da1365fa"
FROZEN_SCHEMA_HASH = "db34d8f1dbd82772d86fc921daa57d7007e748c004bf40b250023d1247823f25"
LIBRARY_INDEX = WPL_ROOT / "library_index.json"
LIBRARY_MANIFEST = WPL_ROOT / "library_freeze_manifest.json"
OVERLAP_MATRIX = WPL_ROOT / "source_overlap_matrix.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def practice_semantic_hash(practice: dict[str, Any]) -> str:
    payload = json.dumps(practice, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def pattern_semantic_hash(pattern: dict[str, Any]) -> str:
    payload = json.dumps(pattern, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def audit_semantic_hash(audit: dict[str, Any]) -> str:
    subset = {
        key: audit[key]
        for key in audit
        if key not in {"review_timestamp", "audit_hash"}
    }
    payload = json.dumps(subset, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def load_pilot_patterns() -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    for path in sorted(PILOT_DIR.glob("*.json")):
        patterns.append(json.loads(path.read_text(encoding="utf-8")))
    return patterns


def load_pilot_practices() -> list[dict[str, Any]]:
    if not PRACTICE_DIR.is_dir():
        return []
    practices: list[dict[str, Any]] = []
    for path in sorted(PRACTICE_DIR.glob("*.json")):
        practices.append(json.loads(path.read_text(encoding="utf-8")))
    return practices


def load_pilot_practice_index() -> dict[str, Any]:
    return json.loads(PILOT_PRACTICE_INDEX.read_text(encoding="utf-8"))


def load_pilot_source_support_map() -> dict[str, Any]:
    return json.loads(PILOT_SOURCE_SUPPORT_MAP.read_text(encoding="utf-8"))


def load_pilot_index() -> dict[str, Any]:
    return json.loads(PILOT_INDEX.read_text(encoding="utf-8"))


def load_pilot_manifest() -> dict[str, Any]:
    return json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))


def load_pilot_audit_records() -> list[dict[str, Any]]:
    return json.loads(PILOT_AUDITS.read_text(encoding="utf-8"))


def pilot_semantic_manifest_subset(manifest: dict[str, Any]) -> dict[str, Any]:
    subset = {
        "pilot_version": manifest["pilot_version"],
        "pattern_ids": manifest["pattern_ids"],
        "pattern_hashes": manifest["pattern_hashes"],
        "source_workflow_ids": manifest["source_workflow_ids"],
        "source_workflow_hashes": manifest["source_workflow_hashes"],
        "manual_audit_ids": manifest["manual_audit_ids"],
        "status": manifest["status"],
    }
    if "practice_ids" in manifest:
        subset["practice_ids"] = manifest["practice_ids"]
        subset["practice_hashes"] = manifest["practice_hashes"]
    if "source_support_map_hash" in manifest:
        subset["source_support_map_hash"] = manifest["source_support_map_hash"]
    subset["bundle_hash"] = manifest["bundle_hash"]
    return subset


def pilot_semantic_hash(manifest: dict[str, Any]) -> str:
    payload = json.dumps(
        pilot_semantic_manifest_subset(manifest),
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_bytes(payload.encode("utf-8"))


def load_core_patterns() -> list[dict[str, Any]]:
    if not CORE_DIR.is_dir():
        return []
    patterns: list[dict[str, Any]] = []
    for path in sorted(CORE_DIR.glob("*.json")):
        patterns.append(json.loads(path.read_text(encoding="utf-8")))
    return patterns


def load_core_practices() -> list[dict[str, Any]]:
    if not CORE_PRACTICE_DIR.is_dir():
        return []
    practices: list[dict[str, Any]] = []
    for path in sorted(CORE_PRACTICE_DIR.glob("*.json")):
        practices.append(json.loads(path.read_text(encoding="utf-8")))
    return practices


def load_core_manifest() -> dict[str, Any]:
    return json.loads(CORE_MANIFEST.read_text(encoding="utf-8"))


def load_core_index() -> dict[str, Any]:
    return json.loads(CORE_INDEX.read_text(encoding="utf-8"))


def load_core_audit_records() -> list[dict[str, Any]]:
    return json.loads(CORE_AUDITS.read_text(encoding="utf-8"))


def load_core_source_support_map() -> dict[str, Any]:
    return json.loads(CORE_SOURCE_SUPPORT_MAP.read_text(encoding="utf-8"))


def load_core_practice_index() -> dict[str, Any]:
    return json.loads(CORE_PRACTICE_INDEX.read_text(encoding="utf-8"))


def core_semantic_manifest_subset(manifest: dict[str, Any]) -> dict[str, Any]:
    subset = {
        "core_version": manifest["core_version"],
        "pilot_pattern_refs": manifest["pilot_pattern_refs"],
        "core_pattern_ids": manifest["core_pattern_ids"],
        "core_pattern_hashes": manifest["core_pattern_hashes"],
        "practice_ids": manifest["practice_ids"],
        "practice_hashes": manifest["practice_hashes"],
        "source_catalog_hash": manifest["source_catalog_hash"],
        "schema_bundle_hash": manifest["schema_bundle_hash"],
        "source_support_map_hash": manifest["source_support_map_hash"],
        "status": manifest["status"],
        "bundle_hash": manifest["bundle_hash"],
    }
    return subset


def core_semantic_hash(manifest: dict[str, Any]) -> str:
    payload = json.dumps(
        core_semantic_manifest_subset(manifest),
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_bytes(payload.encode("utf-8"))


def source_support_map_semantic_hash(support_map: dict[str, Any]) -> str:
    version_key = "core_version" if "core_version" in support_map else "pilot_version"
    subset = {
        version_key: support_map[version_key],
        "program_phase": support_map["program_phase"],
        "entries": support_map["entries"],
    }
    payload = json.dumps(subset, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def load_library_index() -> dict[str, Any]:
    return json.loads(LIBRARY_INDEX.read_text(encoding="utf-8"))


def load_library_manifest() -> dict[str, Any]:
    return json.loads(LIBRARY_MANIFEST.read_text(encoding="utf-8"))


def load_overlap_matrix() -> dict[str, Any]:
    return json.loads(OVERLAP_MATRIX.read_text(encoding="utf-8"))
