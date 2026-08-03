"""Strict quality gate for content drafts (Phase H2.8)."""

from __future__ import annotations

import re

from app.schemas.contracts import (
    ContentClaim,
    ContentDraftQualityCheck,
    ContentDraftResult,
    ContentQualityGateDecision,
)
from app.services.content_claim_verification import (
    cta_duplicated_in_body,
    has_unsupported_exact_statistic,
)

_DIMENSION_WEIGHTS: dict[str, float] = {
    "instruction_adherence": 0.08,
    "domain_depth": 0.14,
    "audience_fit": 0.08,
    "platform_fit": 0.06,
    "factual_safety": 0.14,
    "structure": 0.08,
    "clarity": 0.08,
    "originality": 0.08,
    "repetition": 0.1,
    "cta_quality": 0.08,
    "language_quality": 0.04,
    "professional_credibility": 0.04,
}

_CRITICAL_CODES = frozenset(
    {
        "duplicated_final_cta",
        "unsupported_exact_statistic",
        "invented_statistic",
        "raw_technical_terminology",
        "generic_filler_dominates",
    }
)


def run_strict_quality_gate(
    result: ContentDraftResult,
    *,
    editorial_issues: list[str],
    editorial_scores: dict[str, float],
    claims: list[ContentClaim],
    locale: str = "ru",
) -> ContentDraftQualityCheck:
    issues = list(editorial_issues)
    critical: list[str] = []

    blob = " ".join([result.hook, result.body, result.cta, *result.variants])
    schema_valid = bool(result.skill_code)
    required_present = bool(result.hook.strip() and result.body.strip() and result.cta.strip())
    if not required_present:
        issues.append("missing_required_fields")

    no_secrets = not re.search(
        r"(sk-[A-Za-z0-9]{10,}|api[_-]?key|y0__[A-Za-z0-9])", blob, re.I
    )
    if not no_secrets:
        issues.append("possible_secret_leak")
        critical.append("raw_technical_terminology")

    if has_unsupported_exact_statistic(claims):
        issues.append("unsupported_exact_statistic")
        critical.append("unsupported_exact_statistic")

    if cta_duplicated_in_body(result):
        issues.append("duplicated_final_cta")
        critical.append("duplicated_final_cta")

    if re.search(r"Маршрут:|content\.telegram_post|knowledge snapshot", blob, re.I):
        critical.append("raw_technical_terminology")

    dimension_scores = dict(editorial_scores)
    dimension_scores.setdefault("factual_safety", 0.9 if not has_unsupported_exact_statistic(claims) else 0.1)
    dimension_scores.setdefault("structure", 1.0 if required_present else 0.2)
    dimension_scores.setdefault("platform_fit", 0.85)
    dimension_scores.setdefault("instruction_adherence", 0.85)
    dimension_scores.setdefault("clarity", 0.8)
    dimension_scores.setdefault("language_quality", dimension_scores.get("clarity", 0.8))

    total_w = sum(_DIMENSION_WEIGHTS.values())
    score = round(
        sum(dimension_scores.get(k, 0.5) * w for k, w in _DIMENSION_WEIGHTS.items()) / total_w,
        3,
    )

    if dimension_scores.get("originality", 1.0) < 0.45:
        issues.append("generic_filler_dominates")
        critical.append("generic_filler_dominates")

    gate_decision = ContentQualityGateDecision.BLOCK
    if critical:
        if score >= 0.70 and "duplicated_final_cta" in critical:
            gate_decision = ContentQualityGateDecision.REVISE
        else:
            gate_decision = ContentQualityGateDecision.BLOCK
    elif score >= 0.85:
        gate_decision = ContentQualityGateDecision.PASS
    elif score >= 0.70:
        gate_decision = ContentQualityGateDecision.REVISE
    else:
        gate_decision = ContentQualityGateDecision.BLOCK

    passed = gate_decision == ContentQualityGateDecision.PASS
    checks = {
        "schema_valid": schema_valid,
        "required_fields_present": required_present,
        "locale_ok": True,
        "no_unsupported_claims": not has_unsupported_exact_statistic(claims),
        "no_secrets": no_secrets,
        "length_ok": len(result.body) >= 280,
    }

    return ContentDraftQualityCheck(
        passed=passed,
        schema_valid=schema_valid,
        required_fields_present=required_present,
        locale_ok=True,
        no_unsupported_claims=checks["no_unsupported_claims"],
        no_secrets=no_secrets,
        checks=checks,
        issues=sorted(set(issues)),
        score=score,
        dimension_scores=dimension_scores,
        critical_failures=sorted(set(critical)),
        gate_decision=gate_decision,
    )
