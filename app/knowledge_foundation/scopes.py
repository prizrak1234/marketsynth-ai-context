"""Tenant / project knowledge scope boundaries."""

from __future__ import annotations

from uuid import UUID

from app.schemas.contracts import KnowledgeItem, KnowledgeTenantScope


class KnowledgeScopeError(PermissionError):
    """Raised when retrieval would cross tenant or project boundaries."""


def is_cross_tenant_denied(
    item: KnowledgeItem,
    *,
    requester_owner_id: UUID | None,
    requester_project_id: UUID | None = None,
) -> bool:
    if item.tenant_scope == KnowledgeTenantScope.GLOBAL:
        return False
    if item.tenant_scope == KnowledgeTenantScope.OWNER:
        if requester_owner_id is None or item.owner_id is None:
            return True
        return item.owner_id != requester_owner_id
    if item.tenant_scope == KnowledgeTenantScope.PROJECT:
        if (
            requester_owner_id is None
            or requester_project_id is None
            or item.owner_id is None
            or item.project_id is None
        ):
            return True
        if item.owner_id != requester_owner_id:
            return True
        return item.project_id != requester_project_id
    return True


def assert_retrieval_allowed(
    item: KnowledgeItem,
    *,
    requester_owner_id: UUID | None,
    requester_project_id: UUID | None = None,
) -> None:
    if is_cross_tenant_denied(
        item,
        requester_owner_id=requester_owner_id,
        requester_project_id=requester_project_id,
    ):
        raise KnowledgeScopeError(
            f"cross_scope_denied:{item.id}:{item.tenant_scope.value}"
        )
