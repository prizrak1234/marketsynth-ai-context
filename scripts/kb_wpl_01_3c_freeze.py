"""Build KB-WPL-01.3C library freeze artifacts — audit only, no pattern changes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.knowledge.workflow_patterns.library_freeze import (
    build_library_freeze_manifest,
    build_library_index,
    build_overlap_matrix,
    library_index_semantic_hash,
    library_semantic_hash,
    overlap_matrix_semantic_hash,
)

REPO = Path(__file__).resolve().parents[1]
WPL_ROOT = REPO / "packages" / "knowledge" / "workflow_patterns" / "0.1.0"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_freeze() -> dict:
    generated_at = datetime.now(UTC).isoformat()
    index = build_library_index(generated_at=generated_at)
    overlap = build_overlap_matrix()
    manifest = build_library_freeze_manifest(generated_at=generated_at)

    _write_json(WPL_ROOT / "library_index.json", index)
    _write_json(WPL_ROOT / "source_overlap_matrix.json", overlap)
    _write_json(WPL_ROOT / "library_freeze_manifest.json", manifest)

    return {
        "pattern_count": manifest["pattern_count"],
        "unique_practice_count": manifest["unique_practice_count"],
        "audit_record_count": manifest["audit_record_count"],
        "library_index_hash": library_index_semantic_hash(index),
        "overlap_matrix_hash": overlap_matrix_semantic_hash(overlap),
        "library_semantic_hash": library_semantic_hash(manifest),
        "library_bundle_hash": manifest.get("library_semantic_hash"),
        "status": manifest["status"],
        "runtime_authorized": manifest["runtime_authorized"],
        "production_eligible": manifest["production_eligible"],
    }


def main() -> None:
    print(build_freeze())


if __name__ == "__main__":
    main()
