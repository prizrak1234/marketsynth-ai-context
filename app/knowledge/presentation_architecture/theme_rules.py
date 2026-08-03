"""Theme recommendation rules for Presentation Architecture."""

from __future__ import annotations

from typing import Any

from app.knowledge.presentation_architecture.contracts import THEME_FAMILIES


def validate_theme_recommendation(
    theme: dict[str, Any],
    *,
    brand_constraints: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    family = theme.get("theme_family")
    if family not in THEME_FAMILIES:
        errors.append("invalid_theme_family")
    if theme.get("provider_neutral") is not True:
        errors.append("theme_must_be_provider_neutral")
    if family == "custom_brand" and not (brand_constraints or theme.get("brand_fit")):
        errors.append("custom_brand_requires_brand_constraints")
    if theme.get("remote_font_url"):
        errors.append("remote_font_reference_rejected")
    if family in {"dark", "colorful"} and not theme.get("accessibility"):
        errors.append("dark_or_colorful_theme_requires_contrast_review")
    return errors
