"""Narrative arc validation."""

from __future__ import annotations

from typing import Any

from app.knowledge.presentation_architecture.contracts import ARC_TYPES


def validate_narrative_arc(arc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if arc.get("arc_type") not in ARC_TYPES:
        errors.append("invalid_arc_type")
    for field in ("arc_id", "opening", "conclusion", "provenance"):
        if not arc.get(field):
            errors.append(f"missing_narrative_field:{field}")
    return errors
