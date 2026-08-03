"""Semantic validation for ms.skill.presentation_architecture."""

from __future__ import annotations

import json
import re
from typing import Any

from app.knowledge.n8n_engineering.pattern_selection import validate_pattern_selection_list
from app.knowledge.presentation_architecture.accessibility import (
    validate_accessibility_requirements,
)
from app.knowledge.presentation_architecture.contracts import (
    FORBIDDEN_OUTPUT_FIELDS,
    PRESENTATION_READINESS,
    PRESENTATION_TYPES,
)
from app.knowledge.presentation_architecture.narrative import validate_narrative_arc
from app.knowledge.presentation_architecture.slide_rules import validate_slide_plan
from app.knowledge.presentation_architecture.theme_rules import validate_theme_recommendation

CSS_PATTERN = re.compile(r"(\{[^}]*:\s*[^}]+;|@import|font-face)", re.I)
HTML_PATTERN = re.compile(r"(<html|<body|<style|<script)", re.I)
REMOTE_FONT_PATTERN = re.compile(r"(fonts\.googleapis|fonts\.gstatic|@font-face)", re.I)


def _contains_forbidden_markup(payload: dict[str, Any]) -> list[str]:
    blob = json.dumps(payload)
    errors: list[str] = []
    if CSS_PATTERN.search(blob):
        errors.append("raw_css_rejected")
    if HTML_PATTERN.search(blob):
        errors.append("raw_html_rejected")
    if REMOTE_FONT_PATTERN.search(blob):
        errors.append("remote_font_rejected")
    return errors


def validate_chart_requirement(chart: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not chart.get("data_reference"):
        errors.append("chart_requires_data_reference")
    if chart.get("truncated_axis") and not chart.get("uncertainty_notes"):
        errors.append("misleading_scale_flagged")
    return errors


def validate_presentation_input(payload: dict[str, Any]) -> list[str]:
    errors = _contains_forbidden_markup(payload)
    if payload.get("presentation_type") and payload["presentation_type"] not in PRESENTATION_TYPES:
        errors.append("invalid_presentation_type")
    for claim in payload.get("prohibited_claims") or []:
        if claim in json.dumps(payload.get("source_content_references") or []):
            errors.append("prohibited_claim_in_source")
    return errors


def validate_presentation_output(payload: dict[str, Any]) -> list[str]:
    errors = _contains_forbidden_markup(payload)
    for field in FORBIDDEN_OUTPUT_FIELDS:
        if field in payload:
            errors.append(f"forbidden_output_field:{field}")
    readiness = payload.get("presentation_readiness")
    if readiness and readiness not in PRESENTATION_READINESS:
        errors.append("invalid_presentation_readiness")
    arc = payload.get("narrative_arc") or {}
    if arc:
        errors.extend(validate_narrative_arc(arc))
    slides = payload.get("slide_plan") or []
    if slides:
        errors.extend(validate_slide_plan(slides))
    theme = payload.get("theme_recommendation") or {}
    if theme:
        errors.extend(
            validate_theme_recommendation(
                theme,
                brand_constraints=payload.get("brand_constraints"),
            )
        )
    accessibility = payload.get("accessibility_requirements") or {}
    if accessibility:
        errors.extend(validate_accessibility_requirements(accessibility))
    for chart in payload.get("chart_requirements") or []:
        errors.extend(validate_chart_requirement(chart))
    for finding in payload.get("claim_safety_findings") or []:
        if (
            isinstance(finding, dict)
            and finding.get("severity") == "blocking"
            and readiness == "ready_for_rendering_review"
        ):
            errors.append("claim_risk_blocks_ready")
    pattern_refs = payload.get("pattern_references") or []
    if pattern_refs:
        errors.extend(validate_pattern_selection_list(pattern_refs))
    cta = payload.get("CTA_strategy") or {}
    objective = payload.get("presentation_objective", "")
    if cta.get("primary_action") and objective and cta.get("aligned_with_objective") is False:
        errors.append("cta_not_aligned_with_objective")
    if payload.get("presentation_type") == "investor_presentation":
        projections = payload.get("unsupported_claims") or []
        if (
            projections
            and readiness == "ready_for_rendering_review"
            and not payload.get("assumptions")
        ):
            errors.append("investor_projections_require_assumptions")
    return errors


def validate_prohibited_claim(
    claim: str,
    *,
    prohibited: list[str],
    key_messages: list[str],
) -> list[str]:
    errors: list[str] = []
    if claim in prohibited and claim in key_messages:
        errors.append("prohibited_claim_as_key_message")
    return errors
