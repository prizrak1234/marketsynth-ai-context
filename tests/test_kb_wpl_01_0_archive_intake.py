"""KB-WPL-01.0 — Archive intake freeze tests."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INTAKE_DOCS = REPO / "docs" / "research" / "archive-intake"


def _load_inventory() -> dict:
    return json.loads((INTAKE_DOCS / "archive-checksums.json").read_text(encoding="utf-8"))


def test_01_intake_docs_exist() -> None:
    for name in (
        "README.md",
        "ARCHIVE-BOTS-KNOWLEDGE-INTAKE.md",
        "archive-inventory.md",
        "archive-checksums.json",
        "source-risk-register.md",
        "license-provenance-report.md",
        "duplicate-content-report.md",
        "adopt-adapt-quarantine-reject-matrix.md",
    ):
        assert (INTAKE_DOCS / name).is_file(), name


def test_02_four_archives_inventoried() -> None:
    data = _load_inventory()
    assert data["program"] == "KB-WPL-01.0"
    assert len(data["archives"]) == 4
    assert data["file_count"] >= 375


def test_03_required_inventory_fields() -> None:
    required = {
        "archive_id",
        "archive_name",
        "archive_hash",
        "file_path",
        "file_name",
        "file_extension",
        "file_size",
        "file_hash",
        "content_type",
        "source_category",
        "executable_content",
        "workflow_content",
        "script_content",
        "network_instructions",
        "credential_markers",
        "provider_dependencies",
        "license_status",
        "provenance_status",
        "duplicate_group",
        "trust_status",
        "decision",
        "target_component",
        "blockers",
        "notes",
    }
    data = _load_inventory()
    for entry in data["entries"]:
        missing = required - set(entry.keys())
        assert not missing, f"missing {missing} in {entry['file_path']}"


def test_04_workflow_json_quarantined() -> None:
    data = _load_inventory()
    wfs = [e for e in data["entries"] if e.get("workflow_content")]
    assert len(wfs) >= 240
    for wf in wfs:
        assert wf["decision"] == "quarantine"
        assert wf["trust_status"] == "quarantined"
        assert wf["target_component"] == "workflow_catalog_quarantine"


def test_05_external_skills_quarantined() -> None:
    data = _load_inventory()
    skills = [e for e in data["entries"] if e["source_category"] == "skill_package"]
    assert len(skills) >= 2
    for s in skills:
        assert s["decision"] == "quarantine"
        assert "adapt_methodology_required" in s["blockers"]


def test_06_scripts_quarantined_never_execute() -> None:
    data = _load_inventory()
    scripts = [e for e in data["entries"] if e.get("script_content")]
    assert scripts
    for s in scripts:
        assert s["decision"] == "quarantine"
        assert "never_execute" in s["blockers"]


def test_07_no_absolute_paths_in_portable_metadata() -> None:
    data = _load_inventory()
    for entry in data["entries"]:
        rel = entry["file_path"]
        assert not rel.startswith("C:")
        assert not rel.startswith("/Users/")
        assert ".." not in rel


def test_08_path_traversal_not_in_inventory() -> None:
    data = _load_inventory()
    for entry in data["entries"]:
        assert "../" not in entry["file_path"]
        assert "..\\" not in entry["file_path"]


def test_09_workflow_risk_counts_documented() -> None:
    data = _load_inventory()
    wfs = [e for e in data["entries"] if e.get("workflow_content")]
    code = sum(1 for e in wfs if e.get("code_nodes"))
    cred = sum(1 for e in wfs if e.get("credential_markers"))
    pub = sum(1 for e in wfs if e.get("publication_nodes"))
    assert code > 0
    assert cred > 0
    assert pub > 0
    risk_doc = (INTAKE_DOCS / "source-risk-register.md").read_text(encoding="utf-8")
    assert str(code) in risk_doc
    assert str(cred) in risk_doc


def test_10_not_make_blueprints_note() -> None:
    data = _load_inventory()
    assert "NOT Make" in data["note"] or "not Make" in data["note"].lower()
    bots_doc = (INTAKE_DOCS / "ARCHIVE-BOTS-KNOWLEDGE-INTAKE.md").read_text(encoding="utf-8")
    assert "NOT Make" in bots_doc or "n8n exports" in bots_doc
