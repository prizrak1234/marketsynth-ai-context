"""Workflow catalog read-only queries — no install/deploy/execute."""

from __future__ import annotations

import json
from pathlib import Path

from app.knowledge.workflow_catalog.contracts import (
    DuplicateFamily,
    WorkflowCatalogBundle,
    WorkflowTemplateRecord,
)
from app.knowledge.workflow_catalog.errors import WorkflowCatalogError

_CATALOG_PATH = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "knowledge"
    / "workflow_catalog"
    / "0.1.0"
    / "catalog.json"
)
_FAMILIES_PATH = _CATALOG_PATH.parent / "duplicate_families.json"


def catalog_path() -> Path:
    return _CATALOG_PATH


def load_catalog(path: Path | None = None) -> WorkflowCatalogBundle:
    target = path or _CATALOG_PATH
    if not target.is_file():
        raise WorkflowCatalogError(f"Workflow catalog not found: {target}")
    payload = json.loads(target.read_text(encoding="utf-8"))
    return WorkflowCatalogBundle.model_validate(payload)


def load_duplicate_families(path: Path | None = None) -> list[DuplicateFamily]:
    target = path or _FAMILIES_PATH
    if not target.is_file():
        return []
    data = json.loads(target.read_text(encoding="utf-8"))
    return [DuplicateFamily.model_validate(item) for item in data.get("families", [])]


def get_workflow_template(
    catalog: WorkflowCatalogBundle,
    workflow_template_id: str,
) -> WorkflowTemplateRecord:
    for template in catalog.templates:
        if template.workflow_template_id == workflow_template_id:
            return template
    raise WorkflowCatalogError(f"Workflow template not found: {workflow_template_id}")


def find_by_capability(
    catalog: WorkflowCatalogBundle,
    capability: str,
) -> list[WorkflowTemplateRecord]:
    return [template for template in catalog.templates if capability in template.categories]


def find_by_provider(
    catalog: WorkflowCatalogBundle,
    provider: str,
) -> list[WorkflowTemplateRecord]:
    needle = provider.lower()
    return [
        template
        for template in catalog.templates
        if any(needle in value.lower() for value in template.providers)
    ]


def find_by_node_type(
    catalog: WorkflowCatalogBundle,
    node_type: str,
) -> list[WorkflowTemplateRecord]:
    needle = node_type.lower()
    return [
        template
        for template in catalog.templates
        if any(needle in value.lower() for value in template.node_types)
    ]


def find_by_trigger(
    catalog: WorkflowCatalogBundle,
    trigger: str,
) -> list[WorkflowTemplateRecord]:
    needle = trigger.lower()
    return [
        template
        for template in catalog.templates
        if any(needle in value.lower() for value in template.trigger_types)
    ]


def find_by_security_finding(
    catalog: WorkflowCatalogBundle,
    finding_type: str,
) -> list[WorkflowTemplateRecord]:
    return [
        template
        for template in catalog.templates
        if any(finding.finding_type == finding_type for finding in template.security_findings)
    ]


def find_by_priority(
    catalog: WorkflowCatalogBundle,
    priority: str,
    statistics_path: Path | None = None,
) -> list[str]:
    """Return workflow IDs matching commercial priority from statistics sidecar."""
    stats_file = statistics_path or (_CATALOG_PATH.parent / "statistics.json")
    if not stats_file.is_file():
        return []
    stats = json.loads(stats_file.read_text(encoding="utf-8"))
    return [
        workflow_id
        for workflow_id, meta in stats.get("by_workflow", {}).items()
        if meta.get("commercial_priority") == priority
    ]


def find_duplicate_family(
    families: list[DuplicateFamily],
    workflow_template_id: str,
) -> DuplicateFamily | None:
    for family in families:
        if workflow_template_id in family.member_workflow_ids:
            return family
    return None


def list_quarantined(catalog: WorkflowCatalogBundle) -> list[WorkflowTemplateRecord]:
    return [
        template
        for template in catalog.templates
        if template.quarantine_status == "quarantined"
    ]


def list_rejected(catalog: WorkflowCatalogBundle) -> list[WorkflowTemplateRecord]:
    return [
        template
        for template in catalog.templates
        if template.quarantine_status == "rejected" or template.adaptation_status == "rejected"
    ]
