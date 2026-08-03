"""Tenant and audit visibility filtering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DiscoveryVisibilityContext:
    tenant_id: str
    project_id: str | None
    internal_audit_mode: bool
    allowed_trust_statuses: frozenset[str]
    include_quarantined: bool
    include_rejected_references: bool


def build_visibility_context(query: dict[str, Any]) -> DiscoveryVisibilityContext:
    allowed = query.get("allowed_trust_statuses") or ["approved", "candidate", "reviewed"]
    return DiscoveryVisibilityContext(
        tenant_id=query["tenant_id"],
        project_id=query.get("project_id"),
        internal_audit_mode=bool(query.get("internal_audit_mode")),
        allowed_trust_statuses=frozenset(allowed),
        include_quarantined=bool(query.get("include_quarantined")),
        include_rejected_references=bool(query.get("include_rejected_references")),
    )


def is_skill_visible(skill: dict[str, Any], ctx: DiscoveryVisibilityContext) -> bool:
    scope = skill.get("tenant_scope", "global")
    if scope == "global":
        return True
    if scope == "tenant_private":
        return skill.get("tenant_id") == ctx.tenant_id
    if scope == "project_private":
        return (
            skill.get("tenant_id") == ctx.tenant_id
            and skill.get("project_id") == ctx.project_id
        )
    return False


def is_artifact_visible(artifact: dict[str, Any], ctx: DiscoveryVisibilityContext) -> bool:
    trust = artifact.get("trust_status", "approved")
    if trust == "rejected" and not ctx.include_rejected_references:
        return False
    if artifact.get("quarantined") and not (ctx.internal_audit_mode and ctx.include_quarantined):
        return False
    if trust not in ctx.allowed_trust_statuses and trust != "quarantined":
        return False
    tenant_id = artifact.get("tenant_id")
    if tenant_id and tenant_id != ctx.tenant_id:
        return False
    project_id = artifact.get("project_id")
    return not (project_id and ctx.project_id and project_id != ctx.project_id)


def generic_not_found() -> dict[str, str]:
    return {"error": "not_found", "message": "Artifact not found or not visible."}
