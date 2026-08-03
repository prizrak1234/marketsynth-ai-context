"""PatternSelectionReference validation against frozen Workflow Pattern Library."""

from __future__ import annotations

from typing import Any

from app.knowledge.n8n_engineering.constants import (
    FROZEN_LIBRARY_SEMANTIC_HASH,
    KNOWN_PATTERN_IDS,
    PROHIBITED_MATURITY,
)
from app.knowledge.workflow_patterns.serialization import load_library_manifest


def validate_pattern_selection(reference: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    pattern_id = reference.get("pattern_id")
    if not pattern_id:
        return ["pattern_id_required"]
    if pattern_id not in KNOWN_PATTERN_IDS:
        errors.append(f"unknown_pattern_id:{pattern_id}")

    library_hash = reference.get("library_semantic_hash")
    if library_hash != FROZEN_LIBRARY_SEMANTIC_HASH:
        errors.append("library_hash_mismatch")

    maturity = reference.get("maturity")
    if maturity != "reviewed":
        errors.append("maturity_must_be_reviewed")
    if maturity in PROHIBITED_MATURITY:
        errors.append("maturity_above_reviewed")

    if reference.get("runtime_authorized") is not False:
        errors.append("runtime_authorized_must_be_false")

    if not reference.get("selection_reason"):
        errors.append("selection_reason_required")

    manifest = load_library_manifest()
    if pattern_id and pattern_id not in manifest.get("pattern_hashes", {}):
        errors.append("pattern_not_in_frozen_library")

    return errors


def validate_pattern_selection_list(references: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, reference in enumerate(references):
        for err in validate_pattern_selection(reference):
            errors.append(f"[{index}]{err}")
    return errors
