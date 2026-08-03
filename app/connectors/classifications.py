"""Connector tool classification helpers (SKILL-01.5)."""

from __future__ import annotations

from app.connectors.contracts import (
    ConnectorActionType,
    ConnectorApprovalClass,
    ConnectorSideEffectClass,
    ConnectorToolDefinition,
)

WRITE_ACTIONS = frozenset(
    {
        ConnectorActionType.WRITE,
        ConnectorActionType.DELETE,
        ConnectorActionType.ADMIN,
        ConnectorActionType.PUBLISH,
        ConnectorActionType.EXECUTE,
        ConnectorActionType.BILLING,
    }
)


def requires_human_approval(tool: ConnectorToolDefinition) -> bool:
    if tool.approval_class != ConnectorApprovalClass.NONE:
        return True
    if tool.action_type in WRITE_ACTIONS:
        return True
    return bool(tool.billing_sensitive or tool.publication_sensitive or tool.destructive)


def requires_elevated_approval(tool: ConnectorToolDefinition) -> bool:
    return tool.approval_class == ConnectorApprovalClass.ELEVATED_APPROVAL or tool.action_type in {
        ConnectorActionType.DELETE,
        ConnectorActionType.ADMIN,
    }


def is_read_only_no_side_effect(tool: ConnectorToolDefinition) -> bool:
    return (
        tool.action_type == ConnectorActionType.READ
        and tool.side_effect_class == ConnectorSideEffectClass.NONE
        and not tool.destructive
        and not tool.billing_sensitive
        and not tool.publication_sensitive
    )
