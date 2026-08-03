"""Deterministic candidate matching pipeline."""

from __future__ import annotations

from typing import Any

from app.knowledge.discovery.indexes import DiscoveryIndexes, DiscoverySources
from app.knowledge.discovery.tokenization import (
    contains_phrase,
    normalize_text,
    tokenize,
)
from app.knowledge.discovery.visibility import DiscoveryVisibilityContext, is_skill_visible

PLATFORM_CAPABILITY_BINDINGS: dict[str, list[str]] = {
    "n8n": [
        "engineering.workflow_architecture",
        "engineering.workflow_debugging",
        "engineering.deployment_review",
        "engineering.error_recovery",
    ],
}
PLATFORM_RELATED_TOKENS = frozenset(
    {"workflow", "n8n", "deployment", "debug", "debugging", "error", "retry", "deploy"}
)


def _match_record(
    *,
    artifact_id: str,
    artifact_type: str,
    title: str,
    summary: str,
    matched_capability_ids: list[str],
    matched_profession_ids: list[str],
    match_type: str,
    match_strength: float,
    matched_field: str,
    matched_value: str,
    limitations: list[str] | None = None,
    blockers: list[str] | None = None,
    recommended_action: str = "review_workflow_pattern",
    implementation_status: str | None = None,
    readiness: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "candidate_id": f"{artifact_type}:{artifact_id}",
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "title": title,
        "summary": summary,
        "matched_profession_ids": matched_profession_ids,
        "matched_capability_ids": matched_capability_ids,
        "related_skill_ids": [],
        "related_pattern_ids": [],
        "trust_status": "candidate",
        "maturity": "reviewed",
        "implementation_status": implementation_status,
        "readiness": readiness or [],
        "match_reasons": [
            {
                "matched_field": matched_field,
                "matched_value": matched_value,
                "match_type": match_type,
                "match_strength": match_strength,
                "limitations": limitations or [],
            }
        ],
        "ranking_factors": {},
        "blockers": blockers or [],
        "limitations": limitations or [],
        "recommended_action": recommended_action,
        "runtime_authorized": False,
        "tenant_scope": "global",
        "provenance": {"origin": "platform_native", "phase": "KB-WPL-01.8"},
    }


def match_query(
    query: dict[str, Any],
    indexes: DiscoveryIndexes,
    sources: DiscoverySources,
    ctx: DiscoveryVisibilityContext,
) -> dict[str, list[dict[str, Any]]]:
    text = query.get("task_description", "")
    normalized = normalize_text(text)
    tokens = tokenize(text)

    professions: list[dict[str, Any]] = []
    capabilities: list[dict[str, Any]] = []
    skills: list[dict[str, Any]] = []
    patterns: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    connectors: list[dict[str, Any]] = []
    tools: list[dict[str, Any]] = []
    practices: list[dict[str, Any]] = []
    error_patterns: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    seen: set[str] = set()

    def add_candidate(bucket: list[dict[str, Any]], candidate: dict[str, Any]) -> None:
        key = candidate["candidate_id"]
        if key in seen:
            return
        seen.add(key)
        bucket.append(candidate)

    for cap_id in query.get("required_capability_ids") or []:
        cap = indexes.capability_by_id.get(cap_id)
        if cap:
            add_candidate(
                capabilities,
                _match_record(
                    artifact_id=cap_id,
                    artifact_type="capability",
                    title=cap["capability_name"],
                    summary=cap.get("objective", ""),
                    matched_capability_ids=[cap_id],
                    matched_profession_ids=cap.get("profession_ids", []),
                    match_type="exact_id",
                    match_strength=1.0,
                    matched_field="required_capability_ids",
                    matched_value=cap_id,
                    implementation_status=cap.get("implementation_status"),
                    readiness=cap.get("readiness"),
                    recommended_action="use_internal_skill_contract",
                ),
            )

    for alias_phrase, alias in indexes.alias_by_phrase.items():
        if contains_phrase(text, alias_phrase):
            for cap_id in alias.get("capability_ids") or []:
                cap = indexes.capability_by_id.get(cap_id)
                if not cap:
                    continue
                add_candidate(
                    capabilities,
                    _match_record(
                        artifact_id=cap_id,
                        artifact_type="capability",
                        title=cap["capability_name"],
                        summary=cap.get("objective", ""),
                        matched_capability_ids=[cap_id],
                        matched_profession_ids=cap.get("profession_ids", []),
                        match_type="alias",
                        match_strength=0.75,
                        matched_field="alias",
                        matched_value=alias_phrase,
                        implementation_status=cap.get("implementation_status"),
                        readiness=cap.get("readiness"),
                    ),
                )
            for pid in alias.get("pattern_ids") or []:
                pattern = indexes.pattern_by_id.get(pid)
                if pattern:
                    add_candidate(
                        patterns,
                        _match_record(
                            artifact_id=pid,
                            artifact_type="workflow_pattern",
                            title=pattern["title"],
                            summary="Workflow pattern reference.",
                            matched_capability_ids=alias.get("capability_ids", []),
                            matched_profession_ids=[],
                            match_type="alias",
                            match_strength=0.6,
                            matched_field="alias",
                            matched_value=alias_phrase,
                            recommended_action="review_workflow_pattern",
                            limitations=[
                                "Pattern supports but does not replace Skill methodology."
                            ],
                        ),
                    )

    for platform in query.get("platform_constraints") or []:
        platform_key = normalize_text(platform)
        bound_caps = PLATFORM_CAPABILITY_BINDINGS.get(platform_key, [])
        query_mentions_platform = platform_key in normalized or platform_key in tokens
        query_relates_to_platform = any(token in PLATFORM_RELATED_TOKENS for token in tokens)
        if not (query_mentions_platform or query_relates_to_platform or not tokens):
            continue
        for cap_id in bound_caps:
            cap = indexes.capability_by_id.get(cap_id)
            if not cap:
                continue
            add_candidate(
                capabilities,
                _match_record(
                    artifact_id=cap_id,
                    artifact_type="capability",
                    title=cap["capability_name"],
                    summary=cap.get("objective", ""),
                    matched_capability_ids=[cap_id],
                    matched_profession_ids=cap.get("profession_ids", []),
                    match_type="platform_constraint",
                    match_strength=0.65,
                    matched_field="platform_constraints",
                    matched_value=platform_key,
                    implementation_status=cap.get("implementation_status"),
                    readiness=cap.get("readiness"),
                ),
            )

    for provider in query.get("provider_constraints") or []:
        provider_key = normalize_text(provider)
        for cap in indexes.capability_by_id.values():
            providers = [normalize_text(item) for item in cap.get("provider_aliases") or []]
            if provider_key not in providers and provider_key not in cap.get("capability_id", ""):
                continue
            cap_id = cap["capability_id"]
            add_candidate(
                capabilities,
                _match_record(
                    artifact_id=cap_id,
                    artifact_type="capability",
                    title=cap["capability_name"],
                    summary=cap.get("objective", ""),
                    matched_capability_ids=[cap_id],
                    matched_profession_ids=cap.get("profession_ids", []),
                    match_type="provider_constraint",
                    match_strength=0.6,
                    matched_field="provider_constraints",
                    matched_value=provider_key,
                    implementation_status=cap.get("implementation_status"),
                    readiness=cap.get("readiness"),
                ),
            )

    for token in tokens:
        for cap_id in indexes.capability_by_token.get(token, []):
            cap = indexes.capability_by_id.get(cap_id)
            if not cap:
                continue
            add_candidate(
                capabilities,
                _match_record(
                    artifact_id=cap_id,
                    artifact_type="capability",
                    title=cap["capability_name"],
                    summary=cap.get("objective", ""),
                    matched_capability_ids=[cap_id],
                    matched_profession_ids=cap.get("profession_ids", []),
                    match_type="exact_token",
                    match_strength=0.55,
                    matched_field="token",
                    matched_value=token,
                    implementation_status=cap.get("implementation_status"),
                    readiness=cap.get("readiness"),
                ),
            )

    matched_cap_ids = {c["artifact_id"] for c in capabilities}

    for cap_id in sorted(matched_cap_ids):
        for skill_id in indexes.skill_by_capability.get(cap_id, []):
            skill = indexes.skill_by_id.get(skill_id)
            if not skill or not is_skill_visible(skill, ctx):
                continue
            cap = indexes.capability_by_id[cap_id]
            add_candidate(
                skills,
                _match_record(
                    artifact_id=skill_id,
                    artifact_type="internal_skill",
                    title=skill["title"],
                    summary=f"Skill for {cap['capability_name']}.",
                    matched_capability_ids=[cap_id],
                    matched_profession_ids=cap.get("profession_ids", []),
                    match_type="declared_binding",
                    match_strength=0.9,
                    matched_field="capability_skill_binding",
                    matched_value=skill_id,
                    recommended_action="use_internal_skill_contract",
                    limitations=["Non-executable candidate package."],
                ),
            )
        if cap_id not in indexes.skill_by_capability and cap_id in indexes.capability_by_id:
            cap = indexes.capability_by_id[cap_id]
            if cap.get("implementation_status") in {"deferred", "specified"}:
                for gap in indexes.gap_by_capability.get(cap_id, []):
                    add_candidate(
                        gaps,
                        _match_record(
                            artifact_id=gap["gap_id"],
                            artifact_type="capability_gap",
                            title=f"Gap: {cap_id}",
                            summary=gap.get("impact", ""),
                            matched_capability_ids=[cap_id],
                            matched_profession_ids=[gap.get("profession_id", "")],
                            match_type="gap_relation",
                            match_strength=0.85,
                            matched_field="capability_gap",
                            matched_value=gap["gap_id"],
                            blockers=[gap.get("remediation", "")],
                            recommended_action="defer",
                        ),
                    )
        for pid in indexes.pattern_by_capability.get(cap_id, []):
            pattern = indexes.pattern_by_id.get(pid)
            if not pattern:
                continue
            cap = indexes.capability_by_id[cap_id]
            add_candidate(
                patterns,
                _match_record(
                    artifact_id=pid,
                    artifact_type="workflow_pattern",
                    title=pattern["title"],
                    summary="Supporting workflow pattern.",
                    matched_capability_ids=[cap_id],
                    matched_profession_ids=cap.get("profession_ids", []),
                    match_type="declared_binding",
                    match_strength=0.5,
                    matched_field="skill_pattern_binding",
                    matched_value=pid,
                    recommended_action="review_workflow_pattern",
                    limitations=["Pattern cannot replace missing Skill."],
                ),
            )
        for connector_class in indexes.connector_class_by_capability.get(cap_id, []):
            add_candidate(
                connectors,
                _match_record(
                    artifact_id=connector_class,
                    artifact_type="connector_class",
                    title=connector_class,
                    summary="Conceptual connector requirement.",
                    matched_capability_ids=[cap_id],
                    matched_profession_ids=indexes.capability_by_id[cap_id].get(
                        "profession_ids", []
                    ),
                    match_type="declared_binding",
                    match_strength=0.4,
                    matched_field="required_connector_classes",
                    matched_value=connector_class,
                    recommended_action="request_connector_design",
                    limitations=["No Connector activation in discovery phase."],
                ),
            )
        for tool_class in indexes.tool_class_by_capability.get(cap_id, []):
            add_candidate(
                tools,
                _match_record(
                    artifact_id=tool_class,
                    artifact_type="tool_class",
                    title=tool_class,
                    summary="Conceptual tool requirement.",
                    matched_capability_ids=[cap_id],
                    matched_profession_ids=indexes.capability_by_id[cap_id].get(
                        "profession_ids", []
                    ),
                    match_type="declared_binding",
                    match_strength=0.35,
                    matched_field="required_tool_classes",
                    matched_value=tool_class,
                    recommended_action="request_human_review",
                    limitations=["Tool class does not grant permission."],
                ),
            )

    for prof_id in query.get("preferred_profession_ids") or []:
        prof = indexes.profession_by_id.get(prof_id)
        if prof:
            add_candidate(
                professions,
                _match_record(
                    artifact_id=prof_id,
                    artifact_type="profession",
                    title=prof["profession_name"],
                    summary=prof.get("objective", ""),
                    matched_capability_ids=prof.get("capability_ids", []),
                    matched_profession_ids=[prof_id],
                    match_type="exact_id",
                    match_strength=0.95,
                    matched_field="preferred_profession_ids",
                    matched_value=prof_id,
                    recommended_action="request_human_review",
                    limitations=["Profession match does not imply implementation readiness."],
                ),
            )

    if ctx.internal_audit_mode and ctx.include_quarantined:
        for item in sources.quarantined_templates:
            if item.get("tenant_id") and item["tenant_id"] != ctx.tenant_id:
                continue
            add_candidate(
                quarantined,
                _match_record(
                    artifact_id=item["workflow_template_id"],
                    artifact_type="quarantined_workflow_template",
                    title=item.get("title", item["workflow_template_id"]),
                    summary="Quarantined workflow metadata only.",
                    matched_capability_ids=item.get("capability_ids", []),
                    matched_profession_ids=[],
                    match_type="other",
                    match_strength=0.3,
                    matched_field="quarantine",
                    matched_value=item["workflow_template_id"],
                    recommended_action="request_security_review",
                ),
            )

    if ctx.include_rejected_references:
        for item in sources.rejected_artifacts:
            if item.get("tenant_id") and item["tenant_id"] != ctx.tenant_id:
                continue
            add_candidate(
                rejected,
                _match_record(
                    artifact_id=item["artifact_id"],
                    artifact_type="rejected_artifact_reference",
                    title=item.get("title", item["artifact_id"]),
                    summary="Rejected artifact reference.",
                    matched_capability_ids=[],
                    matched_profession_ids=[],
                    match_type="other",
                    match_strength=0.1,
                    matched_field="rejected",
                    matched_value=item["artifact_id"],
                    recommended_action="reject",
                ),
            )

    return {
        "professions": professions,
        "capabilities": capabilities,
        "skills": skills,
        "patterns": patterns,
        "gaps": gaps,
        "connectors": connectors,
        "tools": tools,
        "practices": practices,
        "error_patterns": error_patterns,
        "quarantined": quarantined,
        "rejected": rejected,
    }
