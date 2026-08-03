"""Human-readable discovery explanations."""

from __future__ import annotations

from typing import Any


def explain_candidate(candidate: dict[str, Any]) -> str:
    reasons = candidate.get("match_reasons") or [{}]
    primary = reasons[0]
    return (
        f"{candidate.get('title')} matched via {primary.get('match_type')} "
        f"({primary.get('matched_field')}={primary.get('matched_value')}). "
        f"Rank={candidate.get('total_rank')} confidence={candidate.get('confidence')}."
    )


def explain_route(route: dict[str, Any]) -> str:
    return (
        f"Route {route.get('route_id')}: capabilities="
        f"{', '.join(route.get('required_capability_ids') or [])}; "
        f"skills={', '.join(route.get('candidate_skill_ids') or [])}; "
        f"gaps={', '.join(route.get('capability_gaps') or [])}."
    )
