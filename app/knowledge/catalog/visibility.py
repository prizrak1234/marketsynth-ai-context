"""Tenant visibility for catalog search."""

from __future__ import annotations


def is_audit_mode(mode: str) -> bool:
    return mode == "internal_audit"


def filter_by_tenant(
    records: list[dict],
    *,
    tenant_id: str,
    audit_mode: bool = False,
) -> list[dict]:
    visible: list[dict] = []
    for record in records:
        scope = record.get("tenant_scope", "global")
        trust = record.get("trust_status", "quarantined")
        if trust == "rejected":
            continue
        if trust == "quarantined" and not audit_mode:
            continue
        if scope not in ("global", tenant_id):
            continue
        visible.append(record)
    return visible
