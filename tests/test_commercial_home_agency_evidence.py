"""Commercial Home — honest research evidence gate and routing guards."""

from __future__ import annotations

from pathlib import Path


def test_commercial_home_clears_investigation_redirect_in_service() -> None:
    src = Path("app/services/user_requests_service.py").read_text(encoding="utf-8")
    assert 'home_agency_flow' in src
    assert "row.next_href = None" in src
    assert "row.requires_project = False" in src


def test_commercial_home_attaches_research_skill_for_agency_flow() -> None:
    src = Path("app/domain/user_request_skill_context.py").read_text(encoding="utf-8")
    assert "home_agency_flow" in src
    assert "UserRequestRouteCategory.MARKET_RESEARCH" in src


def test_workspace_home_never_redirects_to_investigation() -> None:
    src = Path("web/src/components/workspace/home/workspace-home-view.tsx").read_text(
        encoding="utf-8"
    )
    assert "window.location.href = lastDto.next_href" not in src
    assert "ResearchCollectionCard" in src


def test_agency_verdict_evidence_gate_in_frontend() -> None:
    src = Path("web/src/lib/home/agency-analysis-flow.ts").read_text(encoding="utf-8")
    assert "assessResearchEvidence" in src
    assert "insufficient_data" in src
    assert "agency.verdict.insufficientData" in src
    assert "hasEvidence" in src


def test_recent_projects_not_linking_investigation_workspace() -> None:
    src = Path("web/src/components/workspace/home/home-recent-projects.tsx").read_text(
        encoding="utf-8"
    )
    assert "/investigation" not in src
    assert 'href="/workspace/projects"' in src
