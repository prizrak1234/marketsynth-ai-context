"""Phase AI.85 — MVP demo freeze invariants."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_freeze_doc_exists() -> None:
    doc = Path("docs/phase_ai_85_mvp_demo_readiness_audit.md")
    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "seed_e2e_demo.py" in text
    assert "demo-flow/status" in text
    assert "provenance/content-production" in text


def test_openapi_includes_demo_and_provenance_paths(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    paths = spec.get("paths", {})
    assert any("demo-flow/status" in key for key in paths)
    assert any("provenance/content-production" in key for key in paths)


def test_seed_script_entrypoint_exists() -> None:
    assert Path("scripts/seed_e2e_demo.py").is_file()
