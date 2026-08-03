"""PRODUCT-01.3A — analysis context specificity gate and snapshot hashing."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.core.security import sanitize_text
from app.schemas.contracts import AnalysisContextFields

_PLACEHOLDER_PATTERNS = (
    r"^бизнес$",
    r"^business$",
    r"^идея$",
    r"^idea$",
    r"^test$",
    r"^тест$",
    r"^example$",
    r"^пример$",
    r"^lorem ipsum",
    r"^your idea here",
    r"^опишите идею",
    r"^например:",
)
_PLACEHOLDER_RE = re.compile("|".join(_PLACEHOLDER_PATTERNS), re.IGNORECASE)
_URL_ONLY_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
_EXPLICIT_UNKNOWN = frozenset({"неизвестно", "unknown", "не знаю", "n/a", "нет данных"})

# Minimum blocking set for PRODUCT-01.3A.3 (Variant B).
BLOCKING_FIELDS = frozenset(
    {
        "idea_description",
        "product_or_service",
        "target_customer",
        "geography",
        "analysis_goal",
    }
)
OPTIONAL_RESEARCH_GAP_FIELDS = (
    "pricing_or_revenue_model",
    "known_competitors",
    "current_stage",
    "budget_context",
)


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, default=str, separators=(",", ":"))


def compute_input_snapshot_hash(fields: AnalysisContextFields) -> str:
    payload = fields.model_dump(mode="json")
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _is_explicit_unknown(value: str | None) -> bool:
    if value is None:
        return False
    return sanitize_text(value).strip().lower() in _EXPLICIT_UNKNOWN


def _idea_invalid(idea: str) -> bool:
    if not idea:
        return True
    if len(idea.split()) <= 1 and len(idea) < 12:
        return True
    if _PLACEHOLDER_RE.match(idea):
        return True
    return bool(_URL_ONLY_RE.match(idea))


def evaluate_specificity(fields: AnalysisContextFields) -> tuple[list[str], list[str]]:
    """Return (missing_fields, warnings)."""
    missing: list[str] = []
    warnings: list[str] = []

    idea = sanitize_text(fields.idea_description or "").strip()
    product = sanitize_text(fields.product_or_service or "").strip()
    target = sanitize_text(fields.target_customer or "").strip()
    geo = sanitize_text(fields.geography or "").strip()
    goal = sanitize_text(fields.analysis_goal or "").strip()

    if _idea_invalid(idea):
        missing.append("idea_description")

    identifiable_product = product
    if not identifiable_product and len(idea.split()) >= 2 and not _PLACEHOLDER_RE.match(idea):
        identifiable_product = idea
    if not identifiable_product:
        missing.append("product_or_service")

    audience_unknown = fields.target_customer_unknown or _is_explicit_unknown(
        fields.target_customer
    )
    if not target and not audience_unknown:
        missing.append("target_customer")
    elif audience_unknown:
        warnings.append("target_customer_unknown")

    geo_unknown = fields.geography_unknown or _is_explicit_unknown(fields.geography)
    if not geo and not geo_unknown:
        missing.append("geography")
    elif geo_unknown:
        warnings.append("geography_unknown")

    if not goal:
        missing.append("analysis_goal")

    for field_name in OPTIONAL_RESEARCH_GAP_FIELDS:
        raw = getattr(fields, field_name, None)
        value = sanitize_text(raw or "").strip()
        if not value or _is_explicit_unknown(value):
            warnings.append(f"research_gap_{field_name}")

    return missing, warnings


def is_specificity_sufficient(fields: AnalysisContextFields) -> bool:
    missing, _ = evaluate_specificity(fields)
    return len(missing) == 0
