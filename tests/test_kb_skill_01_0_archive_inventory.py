"""KB-SKILL-01.0 — Archive inventory and source audit tests."""

from __future__ import annotations

from pathlib import Path

from tests.support.kb_skill_validation import load_archive_checksums

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs" / "research" / "external-archives"


def test_01_inventory_docs_exist() -> None:
    for name in (
        "README.md",
        "source-inventory.md",
        "source-risk-register.md",
        "adopt-adapt-reject-matrix.md",
        "duplicate-content-report.md",
        "license-and-provenance-report.md",
        "archive-checksums.json",
    ):
        assert (DOCS / name).is_file()


def test_02_four_archives_inventoried() -> None:
    data = load_archive_checksums()
    assert len(data["archives"]) == 4
    assert data["file_count"] >= 300


def test_03_every_entry_has_hashes() -> None:
    data = load_archive_checksums()
    for entry in data["entries"]:
        assert len(entry["content_hash"]) == 64
        assert len(entry["archive_hash"]) == 64
        assert entry["license_status"] == "unknown"


def test_04_executable_content_quarantined() -> None:
    data = load_archive_checksums()
    for entry in data["entries"]:
        if entry["executable_content"]:
            assert entry["proposed_decision"] == "QUARANTINE"


def test_05_no_absolute_paths_in_portable_metadata() -> None:
    data = load_archive_checksums()
    for entry in data["entries"]:
        rel = entry["file_path"]
        assert not rel.startswith("C:")
        assert not rel.startswith("/Users/")
        assert ".." not in rel


def test_06_path_traversal_filename_rejected_in_inventory() -> None:
    """Inventory uses relative paths only — traversal patterns must not appear."""
    data = load_archive_checksums()
    for entry in data["entries"]:
        assert "..\\" not in entry["file_path"]
        assert "../" not in entry["file_path"]
