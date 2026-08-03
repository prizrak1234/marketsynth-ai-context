"""Build KB-WPL-01.3A / 01.3A.1 pilot pattern bundle."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.knowledge.workflow_patterns.pilot_definitions import pilot_patterns
from app.knowledge.workflow_patterns.practice_definitions import (
    PATTERN_PRACTICE_IDS,
    pilot_practices,
)
from app.knowledge.workflow_patterns.serialization import (
    audit_semantic_hash,
    pattern_semantic_hash,
    pilot_semantic_hash,
    practice_semantic_hash,
    sha256_bytes,
    source_support_map_semantic_hash,
)
from app.knowledge.workflow_patterns.source_support_definitions import pilot_source_support_map

REPO = Path(__file__).resolve().parents[1]
WPL_ROOT = REPO / "packages" / "knowledge" / "workflow_patterns" / "0.1.0"
PILOT_DIR = WPL_ROOT / "patterns" / "pilot"
PRACTICE_DIR = WPL_ROOT / "practices" / "pilot"
CATALOG_PATH = REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0" / "catalog.json"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_pilot() -> dict:
    from tests.support.wpl_schema_validation import (
        validate_practice_record,
        validate_workflow_pattern,
    )

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    index = {item["workflow_template_id"]: item for item in catalog["templates"]}

    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    PRACTICE_DIR.mkdir(parents=True, exist_ok=True)

    practices = pilot_practices()
    practice_hashes: dict[str, str] = {}
    practice_ids: list[str] = []
    for practice in practices:
        validate_practice_record(practice)
        practice_ids.append(practice["practice_id"])
        path = PRACTICE_DIR / f"{practice['practice_id']}.json"
        path.write_text(json.dumps(practice, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        practice_hashes[practice["practice_id"]] = practice_semantic_hash(practice)

    support_map = pilot_source_support_map()
    support_map_path = WPL_ROOT / "pilot_source_support_map.json"
    support_map_path.write_text(
        json.dumps(support_map, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    support_map_hash = source_support_map_semantic_hash(support_map)

    patterns = pilot_patterns()
    pattern_hashes: dict[str, str] = {}
    source_ids: set[str] = set()
    source_hashes: dict[str, str] = {}

    for pattern in patterns:
        validate_workflow_pattern(pattern)
        assert pattern["source_practice_ids"] == PATTERN_PRACTICE_IDS[pattern["pattern_id"]]
        path = PILOT_DIR / f"{pattern['pattern_id']}.json"
        path.write_text(json.dumps(pattern, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        pattern_hashes[pattern["pattern_id"]] = pattern_semantic_hash(pattern)
        for source_id in pattern["source_workflow_ids"]:
            source_ids.add(source_id)
            template = index[source_id]
            source_hashes[source_id] = template["workflow_hash"]

    generated_at = datetime.now(UTC).isoformat()
    audit_records = []
    for pattern in patterns:
        pattern_id = pattern["pattern_id"]
        entry = next(e for e in support_map["entries"] if e["pattern_id"] == pattern_id)
        audit_payload = {
            "audit_id": f"audit-{pattern_id}",
            "workflow_template_ids": pattern["source_workflow_ids"],
            "pattern_ids": [pattern_id],
            "decision": "approved_for_pilot",
            "rationale": (
                "Lineage hardening crosswalk: catalog metadata + PracticeRecords + "
                f"pattern-specific support signals for {pattern_id}."
            ),
            "limitations": pattern["known_limitations"][:3],
            "program_phase": "KB-WPL-01.3A.1",
            "reviewer_role": "architecture_reviewer_agent",
            "review_method": "catalog_metadata_crosswalk_with_practice_lineage",
            "reviewed_source_ids": entry["source_workflow_ids"],
            "reviewed_practice_ids": entry["source_practice_ids"],
            "review_timestamp": generated_at,
            "owner_review_required": True,
        }
        audit_payload["audit_hash"] = audit_semantic_hash(audit_payload)
        audit_records.append(audit_payload)

    audit_path = WPL_ROOT / "pilot_audit_records.json"
    _write_json(audit_path, audit_records)

    file_hashes = {
        path.name: sha256_bytes(path.read_bytes()) for path in sorted(PILOT_DIR.glob("*.json"))
    }
    for path in sorted(PRACTICE_DIR.glob("*.json")):
        file_hashes[f"practices/pilot/{path.name}"] = sha256_bytes(path.read_bytes())
    file_hashes["pilot_audit_records.json"] = sha256_bytes(audit_path.read_bytes())
    file_hashes["pilot_source_support_map.json"] = sha256_bytes(support_map_path.read_bytes())

    bundle_hash = sha256_bytes(
        json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode()
    )

    manifest = {
        "pilot_version": "0.1.0-pilot-lineage",
        "pattern_ids": sorted(pattern_hashes.keys()),
        "pattern_hashes": pattern_hashes,
        "practice_ids": sorted(practice_ids),
        "practice_hashes": practice_hashes,
        "source_workflow_ids": sorted(source_ids),
        "source_workflow_hashes": source_hashes,
        "manual_audit_ids": [item["audit_id"] for item in audit_records],
        "source_support_map_hash": support_map_hash,
        "file_hashes": file_hashes,
        "bundle_hash": bundle_hash,
        "generated_at": generated_at,
        "status": "pilot_lineage_hardened",
    }
    manifest["semantic_hash"] = pilot_semantic_hash(manifest)

    manifest_path = WPL_ROOT / "pilot_freeze_manifest.json"
    _write_json(manifest_path, manifest)

    practice_index = {
        "pilot_version": manifest["pilot_version"],
        "status": manifest["status"],
        "practice_count": len(practices),
        "practice_ids": manifest["practice_ids"],
        "practice_hashes": practice_hashes,
        "generated_at": generated_at,
    }
    practice_index_path = WPL_ROOT / "pilot_practice_index.json"
    practice_index_path.write_text(
        json.dumps(practice_index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    index_doc = {
        "pilot_version": manifest["pilot_version"],
        "status": manifest["status"],
        "pattern_count": len(patterns),
        "pattern_ids": manifest["pattern_ids"],
        "practice_ids": manifest["practice_ids"],
        "source_workflow_ids": manifest["source_workflow_ids"],
        "source_support_map_hash": support_map_hash,
        "generated_at": generated_at,
    }
    index_path = WPL_ROOT / "pilot_index.json"
    _write_json(index_path, index_doc)

    return {
        "patterns": len(patterns),
        "practices": len(practices),
        "bundle_hash": bundle_hash,
        "semantic_hash": manifest["semantic_hash"],
        "source_support_map_hash": support_map_hash,
    }


def main() -> None:
    stats = build_pilot()
    print(stats)


if __name__ == "__main__":
    main()
