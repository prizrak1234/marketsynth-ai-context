"""Explainable deterministic ranking placeholder — filter-first in KB-SKILL-01.7."""

from __future__ import annotations


def ranking_explanation(matching_fields: list[str]) -> str:
    if not matching_fields:
        return "included_by_filter"
    return f"matched_fields:{','.join(matching_fields)}"
