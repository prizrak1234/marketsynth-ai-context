"""Professional task route construction."""

from __future__ import annotations

from typing import Any

from app.knowledge.discovery.indexes import DiscoveryIndexes


def build_professional_task_route(
    query: dict[str, Any],
    match_buckets: dict[str, list[dict[str, Any]]],
    indexes: DiscoveryIndexes,
) -> dict[str, Any]:
    cap_ids = [c["artifact_id"] for c in match_buckets.get("capabilities", [])]
    prof_ids = [p["artifact_id"] for p in match_buckets.get("professions", [])]
    if not prof_ids and cap_ids:
        first = indexes.capability_by_id.get(cap_ids[0], {})
        prof_ids = list(first.get("profession_ids") or [])[:1]

    skill_ids = [s["artifact_id"] for s in match_buckets.get("skills", [])]
    pattern_ids = [p["artifact_id"] for p in match_buckets.get("patterns", [])]
    connector_classes = [c["artifact_id"] for c in match_buckets.get("connectors", [])]
    tool_classes = [t["artifact_id"] for t in match_buckets.get("tools", [])]
    gap_ids = [g["artifact_id"] for g in match_buckets.get("gaps", [])]

    blockers: list[str] = []
    for gap in match_buckets.get("gaps", []):
        blockers.extend(gap.get("blockers") or [])
    for item in match_buckets.get("skills", []) + match_buckets.get("capabilities", []):
        blockers.extend(item.get("blockers") or [])

    approval_requirements: list[str] = []
    evidence_requirements = list(query.get("required_evidence_classes") or [])
    for cap_id in cap_ids:
        cap = indexes.capability_by_id.get(cap_id, {})
        approval_requirements.extend(cap.get("approval_requirements") or [])

    ordered_caps = _order_capabilities(cap_ids, indexes)

    return {
        "route_id": f"route-{query.get('query_id', 'unknown')}",
        "task_summary": query.get("task_description", ""),
        "selected_profession_ids": prof_ids,
        "required_capability_ids": ordered_caps,
        "candidate_skill_ids": skill_ids,
        "candidate_pattern_ids": pattern_ids,
        "required_connector_classes": sorted(set(connector_classes)),
        "required_tool_classes": sorted(set(tool_classes)),
        "capability_gaps": gap_ids,
        "blockers": sorted(set(blockers)),
        "approval_requirements": sorted(set(approval_requirements)),
        "evidence_requirements": evidence_requirements,
        "route_explanation": "Advisory read-only route — no execution scheduled.",
        "human_review_required": True,
        "runtime_authorized": False,
        "provenance": {"origin": "platform_native", "phase": "KB-WPL-01.8"},
    }


def _order_capabilities(cap_ids: list[str], indexes: DiscoveryIndexes) -> list[str]:
    order_index = {dep["target_capability_id"]: i for i, dep in enumerate(indexes.dependency_graph)}
    return sorted(cap_ids, key=lambda cid: order_index.get(cid, 999))
