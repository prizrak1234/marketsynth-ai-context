"""Slide specification validation rules."""

from __future__ import annotations

from typing import Any

from app.knowledge.presentation_architecture.contracts import MAX_SLIDE_DENSITY_POINTS, SLIDE_TYPES


def _slide_density(slide: dict[str, Any]) -> int:
    points = len(slide.get("supporting_points") or [])
    blocks = len(slide.get("content_blocks") or [])
    return points + blocks


def validate_slide_specification(slide: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if slide.get("slide_type") not in SLIDE_TYPES:
        errors.append("invalid_slide_type")
    if not slide.get("key_message"):
        errors.append("key_message_required")
    unsupported = slide.get("unsupported_or_missing_evidence") or []
    if unsupported and slide.get("key_message") in unsupported:
        errors.append("unsupported_claim_as_key_message")
    for ref in slide.get("evidence_references") or []:
        if isinstance(ref, dict) and not ref.get("source_id"):
            errors.append("evidence_claim_without_source")
    if _slide_density(slide) > MAX_SLIDE_DENSITY_POINTS:
        errors.append("excessive_slide_density")
    return errors


def validate_slide_plan(slides: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    sequences: list[int] = []
    for slide in slides:
        slide_id = slide.get("slide_id")
        if slide_id in seen_ids:
            errors.append(f"duplicate_slide_id:{slide_id}")
        seen_ids.add(slide_id)
        seq = slide.get("sequence_number")
        if isinstance(seq, int):
            sequences.append(seq)
        errors.extend(validate_slide_specification(slide))
    if sequences:
        expected = list(range(1, len(sequences) + 1))
        if sorted(sequences) != expected or len(set(sequences)) != len(sequences):
            errors.append("slide_sequence_not_contiguous")
    return errors
