"""Explainable deterministic ranking."""

from __future__ import annotations

from typing import Any

from app.knowledge.discovery.serialization import load_discovery_bundle


def _confidence(match_strength: float, match_type: str) -> str:
    if match_type in {"exact_id", "declared_binding"} and match_strength >= 0.85:
        return "high"
    if match_strength >= 0.7:
        return "medium"
    if match_strength >= 0.4:
        return "low"
    return "unknown"


def rank_candidates(
    candidates: list[dict[str, Any]],
    *,
    query: dict[str, Any],
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    bundle_weights = weights or load_discovery_bundle()["ranking_weights"]
    sensitivity = query.get("execution_sensitivity", "none")
    ranked: list[dict[str, Any]] = []

    for candidate in candidates:
        reasons = candidate.get("match_reasons") or [{}]
        primary = reasons[0]
        match_type = primary.get("match_type", "other")
        match_strength = float(primary.get("match_strength", 0.0))

        factors = {
            "capability_fit": match_strength * bundle_weights["capability_fit"],
            "explicit_request_fit": (
                bundle_weights["explicit_request_fit"] if match_type == "exact_id" else 0.0
            ),
            "skill_availability": (
                bundle_weights["skill_availability"]
                if candidate.get("artifact_type") == "internal_skill"
                else 0.0
            ),
            "pattern_support": (
                bundle_weights["pattern_support"] * 0.5
                if candidate.get("artifact_type") == "workflow_pattern"
                else 0.0
            ),
            "tenant_visibility": bundle_weights["tenant_visibility"],
            "limitations_penalty": (
                bundle_weights["limitations_penalty"] if candidate.get("limitations") else 0.0
            ),
        }
        penalties: list[str] = []
        blockers = list(candidate.get("blockers") or [])

        if candidate.get("artifact_type") == "workflow_pattern" and match_type == "alias":
            factors["pattern_support"] *= 0.5
            penalties.append("alias_pattern_only")

        if sensitivity in {"billing", "destructive"}:
            factors["execution_sensitivity_compatibility"] = -bundle_weights[
                "execution_sensitivity_compatibility"
            ]
            blockers.append("billing_or_destructive_deny_by_default")
            penalties.append("deny_by_default")

        if candidate.get("artifact_type") == "capability_gap":
            factors["gap_severity"] = bundle_weights["gap_severity"]

        if match_type == "platform_constraint":
            factors["platform_fit"] = bundle_weights["platform_fit"]
        if match_type == "provider_constraint":
            factors["provider_fit"] = bundle_weights["provider_fit"]
        if query.get("required_evidence_classes"):
            factors["evidence_fit"] = bundle_weights["evidence_fit"] * 0.5
        if query.get("approval_constraints"):
            factors["approval_compatibility"] = bundle_weights["approval_compatibility"] * 0.5

        total_rank = round(sum(factors.values()), 4)
        confidence = _confidence(match_strength, match_type)
        if match_type == "exact_token" and confidence == "high":
            confidence = "medium"

        ranked.append(
            {
                **candidate,
                "ranking_factors": factors,
                "total_rank": total_rank,
                "penalties": penalties,
                "blockers": blockers,
                "confidence": confidence,
                "ranking_explanation": (
                    f"{match_type} on {primary.get('matched_field')} "
                    f"with strength {match_strength}"
                ),
            }
        )

    ranked.sort(key=lambda item: (-item["total_rank"], item["artifact_id"]))
    return ranked


def rank_all(
    match_buckets: dict[str, list[dict[str, Any]]],
    query: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    return {key: rank_candidates(items, query=query) for key, items in match_buckets.items()}
