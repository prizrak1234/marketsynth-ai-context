"""Build in-memory artifact index from workflow catalog."""

from __future__ import annotations

from app.knowledge.workflow_catalog.contracts import WorkflowCatalogBundle


def build_artifact_index(catalog: WorkflowCatalogBundle) -> list[dict]:
    index: list[dict] = []
    for t in catalog.templates:
        index.append(
            {
                "artifact_id": t.workflow_template_id,
                "title": t.original_name,
                "artifact_type": "workflow_template",
                "summary": t.use_case or t.original_name,
                "capabilities": t.target_capabilities,
                "source": t.provenance.get("archive_id", "unknown"),
                "trust_status": "quarantined",
                "adaptation_status": t.adaptation_status,
                "security_findings": t.security_findings,
                "tenant_scope": "global",
                "commercial_priority": t.commercial_priority,
                "category": t.category,
                "node_types": t.node_types,
            }
        )
    return index
