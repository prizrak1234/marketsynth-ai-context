"""Capability model bundle serialization and hashing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.knowledge.capability_model.contracts import BUNDLE_VERSION

REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLE_ROOT = REPO_ROOT / "packages" / "knowledge" / "capability_model" / BUNDLE_VERSION
SCHEMAS_DIR = BUNDLE_ROOT / "schemas"
FREEZE_MANIFEST = BUNDLE_ROOT / "freeze_manifest.json"

FROZEN_CAPABILITY_MODEL_BUNDLE_HASH = (
    "e1e2bbeb025a3348944a5dab43e5661d31e2ac559e9e8de4989836c50831e42b"
)
FROZEN_CAPABILITY_MODEL_SEMANTIC_HASH = (
    "20fbd1b9f2e4f4f6f044622e37734824a406c727adff8fb97541266a15bbd633"
)

SEMANTIC_DATA_FILES = (
    "professions.json",
    "capabilities.json",
    "profession_capability_bindings.json",
    "capability_skill_bindings.json",
    "skill_pattern_bindings.json",
    "pattern_connector_bindings.json",
    "connector_tool_bindings.json",
    "capability_dependencies.json",
    "capability_gaps.json",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_professions() -> list[dict[str, Any]]:
    data = load_json(BUNDLE_ROOT / "professions.json")
    assert isinstance(data, list)
    return data


def load_capabilities() -> list[dict[str, Any]]:
    data = load_json(BUNDLE_ROOT / "capabilities.json")
    assert isinstance(data, list)
    return data


def load_capability_skill_bindings() -> list[dict[str, Any]]:
    data = load_json(BUNDLE_ROOT / "capability_skill_bindings.json")
    assert isinstance(data, list)
    return data


def load_skill_pattern_bindings() -> list[dict[str, Any]]:
    data = load_json(BUNDLE_ROOT / "skill_pattern_bindings.json")
    assert isinstance(data, list)
    return data


def load_pattern_connector_bindings() -> list[dict[str, Any]]:
    data = load_json(BUNDLE_ROOT / "pattern_connector_bindings.json")
    assert isinstance(data, list)
    return data


def load_connector_tool_bindings() -> list[dict[str, Any]]:
    data = load_json(BUNDLE_ROOT / "connector_tool_bindings.json")
    assert isinstance(data, list)
    return data


def load_capability_dependencies() -> list[dict[str, Any]]:
    data = load_json(BUNDLE_ROOT / "capability_dependencies.json")
    assert isinstance(data, list)
    return data


def load_capability_gaps() -> list[dict[str, Any]]:
    data = load_json(BUNDLE_ROOT / "capability_gaps.json")
    assert isinstance(data, list)
    return data


def schema_file_hashes() -> dict[str, str]:
    return {path.name: sha256_file(path) for path in sorted(SCHEMAS_DIR.glob("*.json"))}


def semantic_data_hashes() -> dict[str, str]:
    return {name: sha256_file(BUNDLE_ROOT / name) for name in SEMANTIC_DATA_FILES}


def compute_semantic_bundle_hash() -> str:
    """Hash semantic data files only — excludes generated_at."""
    payload = json.dumps(semantic_data_hashes(), sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def load_freeze_manifest() -> dict[str, Any]:
    return load_json(FREEZE_MANIFEST)  # type: ignore[return-value]


def recompute_freeze_manifest_bundle_hash() -> str:
    manifest = load_freeze_manifest()
    payload = json.dumps(manifest["file_hashes"], sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))
