"""KB-SKILL-01.7 — Catalog search read model tests."""

from __future__ import annotations

from app.knowledge.catalog.queries import search_artifacts
from app.knowledge.catalog.visibility import filter_by_tenant


def _index() -> list[dict]:
    return [
        {
            "artifact_id": "art-1",
            "title": "SEO audit workflow pattern",
            "artifact_type": "workflow_template",
            "summary": "Keyword reporting",
            "capabilities": ["seo"],
            "source": "arc-bots-knowledge-rar",
            "trust_status": "quarantined",
            "adaptation_status": "catalog_only",
            "security_findings": [],
            "tenant_scope": "global",
            "category": "seo",
        },
        {
            "artifact_id": "art-2",
            "title": "Rejected unsafe workflow",
            "artifact_type": "workflow_template",
            "summary": "Destructive",
            "capabilities": ["other"],
            "source": "arc-bots-knowledge-rar",
            "trust_status": "rejected",
            "adaptation_status": "rejected",
            "security_findings": ["destructive_sql_pattern"],
            "tenant_scope": "global",
        },
        {
            "artifact_id": "art-3",
            "title": "Tenant B methodology",
            "artifact_type": "methodology",
            "summary": "Private",
            "capabilities": ["engineering"],
            "source": "arc-skills-dlya-peredachi",
            "trust_status": "methodology_approved",
            "adaptation_status": "catalog_only",
            "security_findings": [],
            "tenant_scope": "tenant-b",
        },
    ]


def test_01_quarantined_hidden_from_normal_search() -> None:
    results = search_artifacts(_index(), mode="customer")
    ids = {r.artifact_id for r in results}
    assert "art-1" not in ids


def test_02_quarantined_visible_in_audit_mode() -> None:
    results = search_artifacts(_index(), mode="internal_audit")
    ids = {r.artifact_id for r in results}
    assert "art-1" in ids


def test_03_rejected_excluded_from_search() -> None:
    results = search_artifacts(_index(), mode="internal_audit")
    ids = {r.artifact_id for r in results}
    assert "art-2" not in ids


def test_04_tenant_filtering() -> None:
    visible = filter_by_tenant(_index(), tenant_id="tenant-a", audit_mode=True)
    ids = {r["artifact_id"] for r in visible}
    assert "art-3" not in ids


def test_05_recommended_action_never_install() -> None:
    results = search_artifacts(_index(), mode="internal_audit")
    for r in results:
        assert r.recommended_action not in ("install", "execute", "activate", "deploy")


def test_06_capability_filter() -> None:
    results = search_artifacts(_index(), capability="seo", mode="internal_audit")
    assert all("seo" in r.capabilities for r in results)
