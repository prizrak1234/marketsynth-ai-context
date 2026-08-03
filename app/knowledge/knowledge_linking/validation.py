"""Semantic validation for ms.skill.knowledge_linking."""

from __future__ import annotations

from typing import Any

from app.knowledge.knowledge_linking.contracts import (
    ALLOWED_ARTIFACT_TYPES,
    BROKEN_LINK_FAILURE_TYPES,
    FORBIDDEN_INPUT_FIELDS,
    FORBIDDEN_OUTPUT_FIELDS,
    RESEARCH_STATUS,
)
from app.knowledge.knowledge_linking.relations import (
    ALLOWED_CONFIDENCE,
    ALLOWED_LINK_DIRECTIONS,
    ALLOWED_RELATION_TYPES,
    DETERMINISTIC_EVIDENCE_TYPES,
)
from app.knowledge.knowledge_linking.serialization import build_artifact_index
from app.knowledge.knowledge_linking.visibility import (
    reject_cross_tenant_link,
    resolve_artifact,
)


def validate_knowledge_node(node: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = (
        "artifact_id",
        "artifact_type",
        "title",
        "version",
        "content_hash",
        "tenant_scope",
    )
    for field in required_fields:
        if not node.get(field):
            errors.append(f"missing_node_field:{field}")
    if node.get("artifact_type") not in ALLOWED_ARTIFACT_TYPES:
        errors.append("invalid_artifact_type")
    return errors


def validate_knowledge_link(
    link: dict[str, Any],
    *,
    artifact_index: dict[str, dict[str, Any]],
    tenant_id: str,
    project_id: str | None = None,
    visibility_policy: dict[str, Any] | None = None,
    allowed_relation_types: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    relation = link.get("relation_type")
    allowed = allowed_relation_types or ALLOWED_RELATION_TYPES
    if relation not in allowed:
        errors.append("invalid_relation_type")

    direction = link.get("direction")
    if direction and direction not in ALLOWED_LINK_DIRECTIONS:
        errors.append("invalid_link_direction")

    confidence = link.get("confidence")
    if confidence not in ALLOWED_CONFIDENCE:
        errors.append("invalid_confidence")

    source_id = link.get("source_artifact_id")
    target_id = link.get("target_artifact_id")
    source = resolve_artifact(
        source_id,
        artifact_index,
        tenant_id=tenant_id,
        project_id=project_id,
        visibility_policy=visibility_policy,
    )
    target = resolve_artifact(
        target_id,
        artifact_index,
        tenant_id=tenant_id,
        project_id=project_id,
        visibility_policy=visibility_policy,
    )
    if source is None:
        errors.append("source_not_found")
    if target is None:
        raw_target = artifact_index.get(target_id or "")
        if raw_target and source is not None:
            source_project = artifact_index[source_id].get("project_id")
            target_project = raw_target.get("project_id")
            if source_project and target_project and source_project != target_project:
                errors.append("project_private_mismatch")
            else:
                errors.append("target_not_found")
        else:
            errors.append("target_not_found")

    if source and target:
        raw_source = artifact_index[source_id]
        raw_target = artifact_index[target_id]
        if reject_cross_tenant_link(link, raw_source, raw_target, tenant_id=tenant_id):
            errors.append("cross_tenant_link_rejected")
        source_project = raw_source.get("project_id")
        target_project = raw_target.get("project_id")
        if source_project and target_project and source_project != target_project:
            errors.append("project_private_mismatch")

    evidence = link.get("supporting_evidence") or []
    has_deterministic = any(
        item.get("type") in DETERMINISTIC_EVIDENCE_TYPES
        for item in evidence
        if isinstance(item, dict)
    )
    if confidence == "high" and (not evidence or not has_deterministic):
        errors.append("high_confidence_requires_deterministic_evidence")

    if not link.get("reason"):
        errors.append("link_reason_required")

    return errors


def detect_broken_links(
    artifacts: list[dict[str, Any]],
    *,
    tenant_id: str,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    index = build_artifact_index(artifacts)
    broken: list[dict[str, Any]] = []
    for artifact in artifacts:
        for ref in artifact.get("declared_references") or []:
            target_id = ref.get("target_artifact_id") or ref.get("expected_target_id")
            target = index.get(target_id or "")
            failure_type = None
            blocking = False
            expected_version = ref.get("expected_version")
            expected_hash = ref.get("expected_hash")
            if target is None:
                failure_type = "missing_target"
                blocking = True
            elif expected_version and target.get("version") != expected_version:
                failure_type = "missing_version"
                blocking = True
            elif expected_hash and target.get("content_hash") != expected_hash:
                failure_type = "hash_mismatch"
                blocking = True
            elif ref.get("relation_type") not in ALLOWED_RELATION_TYPES:
                failure_type = "invalid_relation"
            if failure_type:
                broken.append(
                    {
                        "broken_link_id": f"broken-{artifact['artifact_id']}-{target_id}",
                        "source_artifact_id": artifact["artifact_id"],
                        "expected_target_id": target_id,
                        "relation_type": ref.get("relation_type", "related_to"),
                        "failure_type": failure_type,
                        "observed_reference": ref,
                        "expected_reference": {
                            "target_artifact_id": target_id,
                            "version": ref.get("expected_version"),
                            "hash": ref.get("expected_hash"),
                        },
                        "severity": "high" if blocking else "medium",
                        "blocking": blocking,
                        "remediation": "resolve_reference_or_update_index",
                        "provenance": {"detector": "broken_link"},
                    }
                )
    for item in broken:
        if item["failure_type"] not in BROKEN_LINK_FAILURE_TYPES:
            item["failure_type"] = "unknown"
    return broken


def detect_index_recommendations(
    artifacts: list[dict[str, Any]],
    *,
    index_policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    policy = index_policy or {}
    required_indexes = policy.get("required_indexes") or []
    existing = {
        artifact.get("index_membership")
        for artifact in artifacts
        if artifact.get("index_membership")
    }

    for index_type in required_indexes:
        if index_type not in existing:
            recommendations.append(
                {
                    "recommendation_id": f"idx-missing-{index_type}",
                    "index_type": index_type,
                    "scope": policy.get("scope", "tenant"),
                    "missing_or_stale_artifacts": [],
                    "proposed_index_entries": [],
                    "rationale": f"Missing required index: {index_type}",
                    "confidence": "high",
                    "human_review_required": True,
                    "provenance": {"detector": "index_recommendation"},
                }
            )

    for artifact in artifacts:
        if artifact.get("index_stale") is True:
            recommendations.append(
                {
                    "recommendation_id": f"idx-stale-{artifact['artifact_id']}",
                    "index_type": "stale_index_entry",
                    "scope": artifact.get("tenant_scope", "global"),
                    "missing_or_stale_artifacts": [artifact["artifact_id"]],
                    "proposed_index_entries": [
                        {"artifact_id": artifact["artifact_id"], "action": "refresh"}
                    ],
                    "rationale": "Index entry points to stale artifact metadata",
                    "confidence": "medium",
                    "human_review_required": True,
                    "provenance": {"detector": "stale_index"},
                }
            )
    return recommendations


def validate_linking_input(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in FORBIDDEN_INPUT_FIELDS:
        if field in payload:
            errors.append(f"forbidden_input_field:{field}")
    for field in ("analysis_id", "tenant_id", "artifact_scope", "artifacts", "provenance"):
        if not payload.get(field):
            errors.append(f"missing_input_field:{field}")
    for node in payload.get("artifacts") or []:
        errors.extend(validate_knowledge_node(node))
        if not node.get("content_hash"):
            errors.append("authoritative_source_missing_hash")
    return errors


def validate_linking_output(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in FORBIDDEN_OUTPUT_FIELDS:
        if field in payload:
            errors.append(f"forbidden_output_field:{field}")
    status = payload.get("research_status")
    if status not in RESEARCH_STATUS:
        errors.append("invalid_research_status")
    return errors
