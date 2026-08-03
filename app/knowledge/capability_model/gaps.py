"""Capability gap model validation."""

from __future__ import annotations

from typing import Any

from app.knowledge.capability_model.contracts import GAP_TYPES


def validate_capability_gap(gap: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if gap.get("gap_type") not in GAP_TYPES:
        errors.append("invalid_gap_type")
    for field in ("gap_id", "profession_id", "capability_id", "impact", "provenance"):
        if not gap.get(field):
            errors.append(f"missing_gap_field:{field}")
    if gap.get("hidden"):
        errors.append("gap_hidden")
    return errors


def gaps_for_capability(gaps: list[dict[str, Any]], capability_id: str) -> list[dict[str, Any]]:
    return [g for g in gaps if g.get("capability_id") == capability_id]
