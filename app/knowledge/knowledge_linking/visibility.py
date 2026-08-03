"""Tenant and project visibility filtering for Knowledge Linking."""

from __future__ import annotations

from typing import Any

from app.knowledge.knowledge_linking.errors import GENERIC_NOT_FOUND


def is_global_artifact(artifact: dict[str, Any]) -> bool:
    return artifact.get("tenant_scope") == "global"


def is_visible(
    artifact: dict[str, Any],
    *,
    tenant_id: str,
    project_id: str | None = None,
    visibility_policy: dict[str, Any] | None = None,
) -> bool:
    scope = artifact.get("tenant_scope", "global")
    if scope == "global":
        return True
    if scope != tenant_id:
        return False
    project_scope = artifact.get("project_id")
    if project_scope and project_id and project_scope != project_id:
        policy = visibility_policy or {}
        if not policy.get("allow_cross_project_global_refs"):
            return False
    return True


def filter_visible_artifacts(
    artifacts: list[dict[str, Any]],
    *,
    tenant_id: str,
    project_id: str | None = None,
    visibility_policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        artifact
        for artifact in artifacts
        if is_visible(
            artifact,
            tenant_id=tenant_id,
            project_id=project_id,
            visibility_policy=visibility_policy,
        )
    ]


def resolve_artifact(
    artifact_id: str,
    index: dict[str, dict[str, Any]],
    *,
    tenant_id: str,
    project_id: str | None = None,
    visibility_policy: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    artifact = index.get(artifact_id)
    if artifact is None:
        return None
    if not is_visible(
        artifact,
        tenant_id=tenant_id,
        project_id=project_id,
        visibility_policy=visibility_policy,
    ):
        return None
    return artifact


def reject_cross_tenant_link(
    link: dict[str, Any],
    source: dict[str, Any],
    target: dict[str, Any],
    *,
    tenant_id: str,
) -> dict[str, Any] | None:
    source_scope = source.get("tenant_scope", "global")
    target_scope = target.get("tenant_scope", "global")
    if source_scope == "global" or target_scope == "global":
        return None
    if source_scope != target_scope or source_scope != tenant_id:
        return {
            "rejected_link_id": link.get("link_id", "rejected"),
            "source_artifact_id": link.get("source_artifact_id"),
            "target_artifact_id": link.get("target_artifact_id"),
            "reason": "cross_tenant_forbidden",
            "tenant_scope": tenant_id,
            "provenance": link.get("provenance", {}),
        }
    return None


def generic_not_found_error(expected_target_id: str) -> str:
    return GENERIC_NOT_FOUND
