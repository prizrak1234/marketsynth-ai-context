"""Read-only discovery query functions."""

from __future__ import annotations

from typing import Any

from app.knowledge.discovery.filters import raise_if_invalid, validate_query, validate_result
from app.knowledge.discovery.indexes import DiscoverySources, build_indexes, load_default_sources
from app.knowledge.discovery.matching import match_query
from app.knowledge.discovery.ranking import rank_all
from app.knowledge.discovery.routing import build_professional_task_route
from app.knowledge.discovery.serialization import compute_result_hash
from app.knowledge.discovery.visibility import build_visibility_context


def discover(
    query: dict[str, Any],
    sources: DiscoverySources | None = None,
) -> dict[str, Any]:
    raise_if_invalid(validate_query(query))
    src = sources or load_default_sources()
    indexes = build_indexes(src)
    ctx = build_visibility_context(query)
    raw = match_query(query, indexes, src, ctx)
    ranked = rank_all(raw, query)
    limit = query.get("result_limit", 10)
    route = build_professional_task_route(query, ranked, indexes)

    safe_actions = _derive_safe_actions(query, ranked, route)
    readiness_summary = _readiness_summary(ranked)
    missing_components = _missing_components(ranked)

    result = {
        "result_id": f"result-{query['query_id']}",
        "query_id": query["query_id"],
        "mode": query.get("mode", "task_routing"),
        "professions": ranked["professions"][:limit],
        "capabilities": ranked["capabilities"][:limit],
        "skill_candidates": ranked["skills"][:limit],
        "pattern_candidates": ranked["patterns"][:limit],
        "practice_candidates": ranked["practices"][:limit] if ctx.internal_audit_mode else [],
        "error_pattern_candidates": ranked["error_patterns"][:limit]
        if ctx.internal_audit_mode
        else [],
        "connector_requirements": ranked["connectors"][:limit],
        "tool_requirements": ranked["tools"][:limit],
        "capability_gaps": ranked["gaps"][:limit],
        "blockers": route.get("blockers", []),
        "approval_requirements": route.get("approval_requirements", []),
        "evidence_requirements": route.get("evidence_requirements", []),
        "professional_task_route": route,
        "safe_next_actions": safe_actions,
        "readiness_summary": readiness_summary,
        "missing_components": missing_components,
        "unresolved_ambiguities": _ambiguities(query, ranked),
        "limitations": ["Read-only discovery — no install, execute, or deploy."],
        "result_confidence": _aggregate_confidence(ranked),
        "runtime_authorized": False,
        "human_review_required": True,
        "provenance": {"origin": "platform_native", "phase": "KB-WPL-01.8"},
    }
    if ctx.internal_audit_mode and ctx.include_quarantined:
        result["quarantined_workflow_templates"] = ranked["quarantined"][:limit]
    result["result_hash"] = compute_result_hash(result)
    raise_if_invalid(validate_result(result))
    return result


def route_task(query: dict[str, Any], sources: DiscoverySources | None = None) -> dict[str, Any]:
    payload = {**query, "mode": "task_routing"}
    result = discover(payload, sources=sources)
    return result["professional_task_route"]


def find_capabilities(
    task_description: str,
    *,
    tenant_id: str,
    query_id: str = "capability-lookup",
    sources: DiscoverySources | None = None,
) -> list[dict[str, Any]]:
    query = _base_query(query_id, task_description, tenant_id, mode="capability_lookup")
    return discover(query, sources=sources)["capabilities"]


def find_skills(
    task_description: str,
    *,
    tenant_id: str,
    query_id: str = "skill-lookup",
    sources: DiscoverySources | None = None,
) -> list[dict[str, Any]]:
    query = _base_query(query_id, task_description, tenant_id, mode="skill_lookup")
    return discover(query, sources=sources)["skill_candidates"]


def find_patterns(
    task_description: str,
    *,
    tenant_id: str,
    query_id: str = "pattern-lookup",
    sources: DiscoverySources | None = None,
) -> list[dict[str, Any]]:
    query = _base_query(query_id, task_description, tenant_id, mode="workflow_pattern_lookup")
    return discover(query, sources=sources)["pattern_candidates"]


def find_practices(
    task_description: str,
    *,
    tenant_id: str,
    internal_audit_mode: bool = True,
    sources: DiscoverySources | None = None,
) -> list[dict[str, Any]]:
    query = _base_query(
        "practice-lookup", task_description, tenant_id, mode="internal_audit_lookup"
    )
    query["internal_audit_mode"] = internal_audit_mode
    query["include_quarantined"] = internal_audit_mode
    return discover(query, sources=sources)["practice_candidates"]


def find_error_patterns(
    task_description: str,
    *,
    tenant_id: str,
    sources: DiscoverySources | None = None,
) -> list[dict[str, Any]]:
    query = _base_query(
        "error-pattern-lookup",
        task_description,
        tenant_id,
        mode="engineering_diagnosis_lookup",
    )
    query["internal_audit_mode"] = True
    return discover(query, sources=sources)["error_pattern_candidates"]


def _base_query(
    query_id: str, task_description: str, tenant_id: str, *, mode: str
) -> dict[str, Any]:
    return {
        "query_id": query_id,
        "task_description": task_description,
        "tenant_id": tenant_id,
        "mode": mode,
        "execution_sensitivity": "none",
        "result_limit": 10,
        "provenance": {"origin": "platform_native", "phase": "KB-WPL-01.8"},
    }


def _derive_safe_actions(
    query: dict[str, Any],
    ranked: dict[str, list[dict[str, Any]]],
    route: dict[str, Any],
) -> list[str]:
    actions: list[str] = []
    if ranked["skills"]:
        actions.append("use_internal_skill_contract")
    if ranked["patterns"]:
        actions.append("review_workflow_pattern")
    if ranked["gaps"]:
        actions.append("defer")
    if route.get("required_connector_classes"):
        actions.append("request_connector_design")
    if query.get("execution_sensitivity") in {"billing", "destructive", "publication"}:
        actions.append("request_human_review")
    if not actions:
        actions.append("gather_missing_evidence")
    return sorted(set(actions))


def _readiness_summary(ranked: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    has_skill = bool(ranked["skills"])
    has_pattern = bool(ranked["patterns"])
    has_gap = bool(ranked["gaps"])
    return {
        "methodology_available": has_skill,
        "pattern_support_available": has_pattern,
        "runtime_available": False,
        "connector_available": not bool(ranked["connectors"]) or False,
        "blocked": has_gap,
    }


def _missing_components(ranked: dict[str, list[dict[str, Any]]]) -> list[str]:
    missing: list[str] = []
    if ranked["gaps"]:
        missing.append("skill_or_runtime")
    if ranked["connectors"]:
        missing.extend([f"connector:{c['artifact_id']}" for c in ranked["connectors"]])
    if ranked["tools"]:
        missing.extend([f"tool:{t['artifact_id']}" for t in ranked["tools"]])
    return missing


def _ambiguities(query: dict[str, Any], ranked: dict[str, list[dict[str, Any]]]) -> list[str]:
    if len(ranked["capabilities"]) > 3 and "полезное" in query.get("task_description", "").lower():
        return ["Multiple capabilities match ambiguous request."]
    return []


def _aggregate_confidence(ranked: dict[str, list[dict[str, Any]]]) -> str:
    scores = []
    for bucket in ("capabilities", "skills", "patterns"):
        for item in ranked.get(bucket, []):
            scores.append(item.get("confidence"))
    if "high" in scores:
        return "high"
    if "medium" in scores:
        return "medium"
    if "low" in scores:
        return "low"
    return "unknown"
