"""KB-SKILL-01.4 — Knowledge linking analyzer tests."""

from __future__ import annotations

from app.knowledge.linking.analyzer import ArtifactRef, analyze_links, extract_wiki_links


def test_01_extract_wiki_links() -> None:
    links = extract_wiki_links("See [[Target Note]] and [[Other|alias]]")
    assert links == ["Target Note", "Other"]


def test_02_broken_link_detection() -> None:
    artifacts = [
        ArtifactRef(
            "a1",
            "Source",
            existing_links=[{"target_artifact_id": "missing"}],
        ),
    ]
    result = analyze_links(artifacts)
    assert result.broken_links
    assert result.human_review_required


def test_03_orphan_artifacts() -> None:
    artifacts = [ArtifactRef("solo", "Lonely note")]
    result = analyze_links(artifacts)
    assert "solo" in result.orphan_artifacts
