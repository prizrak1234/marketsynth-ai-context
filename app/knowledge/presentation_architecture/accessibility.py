"""Accessibility requirement validation for Presentation Architecture."""

from __future__ import annotations

from typing import Any

REQUIRED_ACCESSIBILITY_FIELDS = (
    "minimum_body_text_guidance",
    "contrast_requirement",
    "color_independence",
    "alt_text_required",
    "chart_description_required",
    "reading_order",
)


def validate_accessibility_requirements(requirements: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_ACCESSIBILITY_FIELDS:
        if not requirements.get(field):
            errors.append(f"missing_accessibility_field:{field}")
    return errors


def theme_requires_contrast_review(theme: dict[str, Any]) -> bool:
    return theme.get("theme_family") in {"dark", "colorful"}
