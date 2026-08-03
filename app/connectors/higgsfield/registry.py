"""Build ConnectorGateway with Higgsfield adapter."""

from __future__ import annotations

from uuid import UUID

from app.connectors.contracts import (
    BudgetPolicy,
    CredentialBindingReference,
    ProjectConnectorBinding,
    TenantConnectorBinding,
)
from app.connectors.gateway import ConnectorGateway
from app.connectors.higgsfield.adapter import HiggsfieldConnectorAdapter
from app.connectors.higgsfield.constants import (
    HIGGSFIELD_CONNECTOR_ID,
    HIGGSFIELD_CONNECTOR_VERSION,
    MEDIA_CANONICAL_OPERATIONS,
)
from app.connectors.higgsfield.descriptor import all_higgsfield_tools, higgsfield_descriptor
from app.core.config import Settings


def build_higgsfield_gateway(settings: Settings) -> ConnectorGateway:
    descriptor = higgsfield_descriptor(settings)
    tools = all_higgsfield_tools()
    adapter = HiggsfieldConnectorAdapter(settings)
    return ConnectorGateway(
        descriptors={descriptor.connector_id: descriptor},
        tools=tools,
        adapters={descriptor.connector_id: adapter},
    )


def build_higgsfield_bindings(
    *,
    tenant_id: UUID,
    project_id: UUID,
    settings: Settings,
) -> tuple[TenantConnectorBinding, ProjectConnectorBinding, CredentialBindingReference | None]:
    if settings.higgsfield_mcp_enabled and settings.higgsfield_sandbox_verified:
        enabled_tools = frozenset(MEDIA_CANONICAL_OPERATIONS)
    else:
        enabled_tools = frozenset()
    credential: CredentialBindingReference | None = None
    if settings.higgsfield_mcp_configured and settings.higgsfield_sandbox_verified:
        credential = CredentialBindingReference(
            binding_id=f"higgsfield-{tenant_id}",
            tenant_id=tenant_id,
            provider="higgsfield",
            connector_id=HIGGSFIELD_CONNECTOR_ID,
            scope_names=("media_render",),
            status="active",
            metadata_only=True,
        )
    tenant = TenantConnectorBinding(
        tenant_id=tenant_id,
        connector_id=HIGGSFIELD_CONNECTOR_ID,
        connector_version=HIGGSFIELD_CONNECTOR_VERSION,
        visible=settings.higgsfield_mcp_enabled,
        enabled_tool_ids=enabled_tools,
        credential_binding_id=credential.binding_id if credential else None,
        runtime_compatible=("operator_sandbox", "media_renderer"),
    )
    project = ProjectConnectorBinding(
        tenant_id=tenant_id,
        project_id=project_id,
        connector_id=HIGGSFIELD_CONNECTOR_ID,
        connector_version=HIGGSFIELD_CONNECTOR_VERSION,
        enabled_tool_ids=enabled_tools,
        credential_binding_id=credential.binding_id if credential else None,
    )
    return tenant, project, credential


def default_render_budget(*, accept_unknown_cost: bool = False) -> BudgetPolicy:
    return BudgetPolicy(
        request_budget_limit=10.0 if not accept_unknown_cost else None,
        approval_threshold=1.0,
        deny_above_limit=not accept_unknown_cost,
    )
