"""CIM schema hashing utilities for freeze manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.knowledge.cim_schema_registry import SCHEMA_FILES, bundle_root

SEMANTIC_MANIFEST_KEYS = (
    "schema_version",
    "canonical_uri_base",
    "schema_status",
    "file_hashes",
    "bundle_hash",
    "source_package_reference",
    "producer_skill",
    "consumer_compatibility",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def schema_file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def compute_file_hashes(version: str = "0.1.0") -> dict[str, str]:
    root = bundle_root(version)
    return {name: schema_file_hash(root / name) for name in SCHEMA_FILES}


def compute_bundle_hash(file_hashes: dict[str, str]) -> str:
    lines = [f"{name}:{file_hashes[name]}" for name in sorted(file_hashes)]
    return sha256_bytes("\n".join(lines).encode("utf-8"))


def semantic_manifest_subset(manifest: dict[str, Any]) -> dict[str, Any]:
    subset = {key: manifest[key] for key in SEMANTIC_MANIFEST_KEYS if key in manifest}
    subset["bundle_hash"] = compute_bundle_hash(subset["file_hashes"])
    return subset


def semantic_manifest_hash(manifest: dict[str, Any]) -> str:
    payload = json.dumps(semantic_manifest_subset(manifest), sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


__all__ = [
    "compute_bundle_hash",
    "compute_file_hashes",
    "schema_file_hash",
    "semantic_manifest_hash",
    "semantic_manifest_subset",
    "sha256_bytes",
]
