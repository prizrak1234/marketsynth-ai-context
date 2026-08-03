"""Discovery bundle serialization and result hashing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.knowledge.discovery.contracts import BUNDLE_VERSION

REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLE_ROOT = REPO_ROOT / "packages" / "knowledge" / "discovery" / BUNDLE_VERSION
FREEZE_MANIFEST = BUNDLE_ROOT / "freeze_manifest.json"

FROZEN_DISCOVERY_BUNDLE_HASH = (
    "9a4f05af83350893fe32ce2bacc6d7c2e963d6440d4d2b47d002a2b1b85304c8"
)

SEMANTIC_DATA_FILES = (
    "aliases.json",
    "ranking_weights.json",
    "query_modes.json",
    "safe_actions.json",
    "discovery_fixtures.json",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_freeze_manifest() -> dict[str, Any]:
    return load_json(FREEZE_MANIFEST)


def load_discovery_bundle() -> dict[str, Any]:
    return {
        "aliases": load_aliases(),
        "ranking_weights": load_json(BUNDLE_ROOT / "ranking_weights.json")["weights"],
        "query_modes": load_json(BUNDLE_ROOT / "query_modes.json")["modes"],
        "safe_actions": load_json(BUNDLE_ROOT / "safe_actions.json")["actions"],
        "fixtures": load_json(BUNDLE_ROOT / "discovery_fixtures.json")["fixtures"],
    }


def load_aliases() -> list[dict[str, Any]]:
    return load_json(BUNDLE_ROOT / "aliases.json")["aliases"]


def compute_semantic_bundle_hash() -> str:
    hashes = {
        name: sha256_bytes((BUNDLE_ROOT / name).read_bytes()) for name in SEMANTIC_DATA_FILES
    }
    payload = json.dumps(hashes, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))


def result_semantic_subset(result: dict[str, Any]) -> dict[str, Any]:
    subset = {key: result[key] for key in result if key not in {"generated_at", "result_hash"}}
    return subset


def compute_result_hash(result: dict[str, Any]) -> str:
    payload = json.dumps(result_semantic_subset(result), sort_keys=True, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))
