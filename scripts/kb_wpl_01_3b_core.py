"""Build KB-WPL-01.3B core pattern library bundle."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.knowledge.workflow_patterns.core_definitions import core_patterns
from app.knowledge.workflow_patterns.core_practice_definitions import (
    CORE_PATTERN_PRACTICE_IDS,
    core_practices,
)
from app.knowledge.workflow_patterns.core_source_support_definitions import (
    core_source_support_map,
)
from app.knowledge.workflow_patterns.serialization import (
    FROZEN_CATALOG_HASH,
    FROZEN_PILOT_BUNDLE_HASH,
    FROZEN_SCHEMA_HASH,
    audit_semantic_hash,
    core_semantic_hash,
    pattern_semantic_hash,
    practice_semantic_hash,
    sha256_bytes,
    source_support_map_semantic_hash,
)

REPO = Path(__file__).resolve().parents[1]
WPL_ROOT = REPO / "packages" / "knowledge" / "workflow_patterns" / "0.1.0"
CORE_DIR = WPL_ROOT / "patterns" / "core"
CORE_PRACTICE_DIR = WPL_ROOT / "practices" / "core"
CATALOG_PATH = REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0" / "catalog.json"
PILOT_MANIFEST_PATH = WPL_ROOT / "pilot_freeze_manifest.json"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_core() -> dict:
    from tests.support.wpl_schema_validation import (
        validate_practice_record,
        validate_workflow_pattern,
    )

    pilot_manifest = json.loads(PILOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if pilot_manifest["bundle_hash"] != FROZEN_PILOT_BUNDLE_HASH:
        msg = "pilot bundle hash drift detected; aborting core build"
        raise RuntimeError(msg)

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    index = {item["workflow_template_id"]: item for item in catalog["templates"]}

    CORE_DIR.mkdir(parents=True, exist_ok=True)
    CORE_PRACTICE_DIR.mkdir(parents=True, exist_ok=True)

    practices = core_practices()
    practice_hashes: dict[str, str] = {}
    for practice in practices:
        validate_practice_record(practice)
        practice_hashes[practice["practice_id"]] = practice_semantic_hash(practice)
        path = CORE_PRACTICE_DIR / f"{practice['practice_id']}.json"
        _write_json(path, practice)

    support_map = core_source_support_map()
    support_map_path = WPL_ROOT / "core_source_support_map.json"
    _write_json(support_map_path, support_map)
    support_map_hash = source_support_map_semantic_hash(support_map)

    patterns = core_patterns()
    core_pattern_hashes: dict[str, str] = {}
    source_ids: set[str] = set()
    source_hashes: dict[str, str] = {}

    for pattern in patterns:
        validate_workflow_pattern(pattern)
        assert pattern["source_practice_ids"] == CORE_PATTERN_PRACTICE_IDS[pattern["pattern_id"]]
        path = CORE_DIR / f"{pattern['pattern_id']}.json"
        _write_json(path, pattern)
        core_pattern_hashes[pattern["pattern_id"]] = pattern_semantic_hash(pattern)
        for source_id in pattern["source_workflow_ids"]:
            source_ids.add(source_id)
            source_hashes[source_id] = index[source_id]["workflow_hash"]

    generated_at = datetime.now(UTC).isoformat()
    audit_records = []
    for pattern in patterns:
        pattern_id = pattern["pattern_id"]
        entry = next(e for e in support_map["entries"] if e["pattern_id"] == pattern_id)
        audit_payload = {
            "audit_id": f"audit-core-{pattern_id}",
            "workflow_template_ids": pattern["source_workflow_ids"],
            "pattern_ids": [pattern_id],
            "decision": "approved_for_core",
            "rationale": (
                "Core library expansion: catalog crosswalk + PracticeRecords + "
                f"support signals for {pattern_id}."
            ),
            "limitations": pattern["known_limitations"][:3],
            "program_phase": "KB-WPL-01.3B",
            "reviewer_role": "architecture_reviewer_agent",
            "review_method": "catalog_metadata_crosswalk_with_practice_lineage",
            "reviewed_source_ids": entry["source_workflow_ids"],
            "reviewed_practice_ids": entry["source_practice_ids"],
            "review_timestamp": generated_at,
            "owner_review_required": True,
        }
        audit_payload["audit_hash"] = audit_semantic_hash(audit_payload)
        audit_records.append(audit_payload)

    audit_path = WPL_ROOT / "core_audit_records.json"
    _write_json(audit_path, audit_records)

    file_hashes = {
        path.name: sha256_bytes(path.read_bytes()) for path in sorted(CORE_DIR.glob("*.json"))
    }
    for path in sorted(CORE_PRACTICE_DIR.glob("*.json")):
        file_hashes[f"practices/core/{path.name}"] = sha256_bytes(path.read_bytes())
    file_hashes["core_audit_records.json"] = sha256_bytes(audit_path.read_bytes())
    file_hashes["core_source_support_map.json"] = sha256_bytes(support_map_path.read_bytes())

    bundle_hash = sha256_bytes(
        json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode()
    )

    all_practice_ids = sorted(practice_hashes.keys())
    manifest = {
        "core_version": "0.1.0-core",
        "pilot_pattern_refs": {
            "pilot_version": pilot_manifest["pilot_version"],
            "pilot_bundle_hash": pilot_manifest["bundle_hash"],
            "pattern_ids": pilot_manifest["pattern_ids"],
            "pattern_hashes": pilot_manifest["pattern_hashes"],
        },
        "core_pattern_ids": sorted(core_pattern_hashes.keys()),
        "core_pattern_hashes": core_pattern_hashes,
        "practice_ids": all_practice_ids,
        "practice_hashes": practice_hashes,
        "source_workflow_ids": sorted(source_ids),
        "source_workflow_hashes": source_hashes,
        "manual_audit_ids": [item["audit_id"] for item in audit_records],
        "source_support_map_hash": support_map_hash,
        "source_catalog_hash": FROZEN_CATALOG_HASH,
        "schema_bundle_hash": FROZEN_SCHEMA_HASH,
        "file_hashes": file_hashes,
        "bundle_hash": bundle_hash,
        "generated_at": generated_at,
        "status": "core_reviewed",
    }
    manifest["semantic_hash"] = core_semantic_hash(manifest)
    _write_json(WPL_ROOT / "core_freeze_manifest.json", manifest)

    practice_index = {
        "core_version": manifest["core_version"],
        "status": manifest["status"],
        "practice_count": len(practices),
        "practice_ids": all_practice_ids,
        "practice_hashes": practice_hashes,
        "generated_at": generated_at,
    }
    _write_json(WPL_ROOT / "core_practice_index.json", practice_index)

    index_doc = {
        "core_version": manifest["core_version"],
        "status": manifest["status"],
        "pilot_pattern_count": len(pilot_manifest["pattern_ids"]),
        "core_pattern_count": len(patterns),
        "total_pattern_count": len(pilot_manifest["pattern_ids"]) + len(patterns),
        "pilot_pattern_ids": pilot_manifest["pattern_ids"],
        "core_pattern_ids": manifest["core_pattern_ids"],
        "generated_at": generated_at,
    }
    _write_json(WPL_ROOT / "core_index.json", index_doc)

    return {
        "core_patterns": len(patterns),
        "total_patterns": len(pilot_manifest["pattern_ids"]) + len(patterns),
        "practices": len(practices),
        "bundle_hash": bundle_hash,
        "semantic_hash": manifest["semantic_hash"],
    }


def main() -> None:
    print(build_core())


if __name__ == "__main__":
    main()
