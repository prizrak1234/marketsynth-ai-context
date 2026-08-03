"""Architecture invariant — Marketsynth Subsystem Standard (H2.8E Slice 0)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_subsystem_standard_documents_exist() -> None:
    assert (ROOT / "docs/architecture/marketsynth_subsystem_standard.md").is_file()
    assert (ROOT / "docs/architecture/adr_subsystem_standard.md").is_file()
    assert (ROOT / "docs/architecture/subsystem_compliance_matrix.md").is_file()
    assert (ROOT / "docs/architecture/README.md").is_file()


def test_agents_and_development_reference_standard() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    development = (ROOT / "docs/DEVELOPMENT.md").read_text(encoding="utf-8")
    assert "marketsynth_subsystem_standard.md" in agents
    assert "Subsystem Standard" in agents or "subsystem_standard" in agents
    assert "marketsynth_subsystem_standard.md" in development
    assert "evaluated against the Marketsynth Subsystem Standard" in agents or (
        "Evaluate against the Subsystem Standard" in development
    )


def test_identity_generation_points_to_standard() -> None:
    h28e = (ROOT / "docs/h2_8e_identity_subsystem.md").read_text(encoding="utf-8")
    runbook = (ROOT / "docs/identity_generation_operator_runbook.md").read_text(
        encoding="utf-8"
    )
    assert "marketsynth_subsystem_standard.md" in h28e
    assert "IdentityQualificationOperator" in h28e
    assert "IdentityReferenceManifest" in h28e
    assert "marketsynth_subsystem_standard.md" in runbook


def test_h28e_did_not_introduce_second_runtime_or_agent_registry() -> None:
    """H2.8E may add identity_generation package, not a parallel Runtime."""
    package = ROOT / "app" / "identity_generation"
    assert package.is_dir()
    banned_names = {
        "runtime.py",
        "agent_registry.py",
        "second_runtime.py",
        "parallel_runtime.py",
    }
    present = {p.name for p in package.glob("*.py")}
    assert present.isdisjoint(banned_names)

    # No second top-level runtime package introduced by this phase.
    assert not (ROOT / "app" / "identity_runtime").exists()
    assert not (ROOT / "app" / "second_runtime").exists()

    text_blob = "\n".join(
        p.read_text(encoding="utf-8").lower()
        for p in package.glob("*.py")
        if p.name != "__init__.py"
    )
    assert "parallel runtime" not in text_blob
    assert "second agent registry" not in text_blob


def test_standard_defines_lifecycle_and_setup_operation_split() -> None:
    standard = (
        ROOT / "docs/architecture/marketsynth_subsystem_standard.md"
    ).read_text(encoding="utf-8")
    for stage in (
        "Discovery",
        "Setup",
        "Configuration",
        "Verification",
        "Readiness",
        "Operation",
        "Review",
        "Maintenance",
        "Deprecation",
    ):
        assert stage in standard
    assert "Setup vs Operation" in standard or "Setup" in standard and "Operation" in standard
    assert "Operator" in standard
    assert "Recipe" in standard
    assert "manifest" in standard.lower()
