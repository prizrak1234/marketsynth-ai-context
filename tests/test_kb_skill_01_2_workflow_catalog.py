"""KB-SKILL-01.2 — legacy tests redirected to KB-WPL-01.2 catalog."""

from __future__ import annotations

import json
from pathlib import Path

from app.knowledge.workflow_catalog.parser import parse_workflow_data
from app.knowledge.workflow_catalog.security_scan import redact_secrets

REPO = Path(__file__).resolve().parents[1]
WF_DOCS = REPO / "docs" / "research" / "workflow-catalog"


def _sample(**overrides: object) -> dict:
    base = {
        "name": "Test SEO Workflow",
        "nodes": [
            {"type": "n8n-nodes-base.manualTrigger", "name": "Start"},
            {"type": "n8n-nodes-base.code", "name": "Transform"},
            {"type": "n8n-nodes-base.telegram", "name": "Publish"},
        ],
        "connections": {},
    }
    base.update(overrides)
    return base


def test_workflow_catalog_docs_exist() -> None:
    for name in ("README.md", "workflow-index.md", "security-findings.md"):
        assert (WF_DOCS / name).is_file()


def test_parse_valid_workflow_json() -> None:
    outcome = parse_workflow_data(_sample(), source_path="test.json", source_path_hash="a" * 64)
    assert outcome.record is not None
    assert outcome.record.quarantine_status == "quarantined"


def test_malformed_json_returns_invalid() -> None:
    outcome = parse_workflow_data({"foo": "bar"}, source_path="x.json", source_path_hash="b" * 64)
    assert outcome.invalid is not None


def test_secrets_redacted() -> None:
    text = 'api_key = "sk-REDACTED"'
    redacted = redact_secrets(text)
    assert "sk-" not in redacted


def test_catalog_json_metadata_only() -> None:
    catalog_path = REPO / "packages" / "knowledge" / "workflow_catalog" / "0.1.0" / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert catalog["valid_exports"] >= 240
    sample = catalog["templates"][0]
    assert "nodes" not in sample
    assert "workflow_hash" in sample
