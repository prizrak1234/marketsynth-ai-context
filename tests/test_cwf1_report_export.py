"""Tests for CWF.1 customer report export."""

from __future__ import annotations

from uuid import uuid4

from app.business_idea_validation.output_enrichment import enrich_output_commercial
from app.business_idea_validation.report_export import (
    build_customer_report_txt,
    validate_export_content,
)
from app.schemas.contracts import (
    BivResearchTerminalState,
    BusinessIdeaValidationVerdictKind,
)
from tests.test_cwf_1a_launch_pack_decision import _output


def test_export_has_no_empty_links_or_raw_codes() -> None:
    base = enrich_output_commercial(
        _output(
            BusinessIdeaValidationVerdictKind.PROCEED_WITH_CONDITIONS,
            research_terminal_state=BivResearchTerminalState.SUCCEEDED_COMPLETE,
            run_id=uuid4(),
        )
    )
    assert base.customer_report is not None
    report = base.customer_report.model_copy(deep=True)
    if report.confirmed_findings:
        finding = report.confirmed_findings[0]
        if finding.sources:
            finding.sources[0].url = "https://example.com/source"
    elif report.confirmed_findings is not None:
        report.confirmed_findings = []
    text = build_customer_report_txt(report=report, output=base, project_name="Demo")
    violations = validate_export_content(text)
    assert "empty_markdown_links" not in violations
    assert "[Смотреть рейтинг]()" not in text
    assert "MARKETSYNTH" in text


def test_export_rejects_empty_markdown_in_validation() -> None:
    bad = "Verdict\n[broken link]()\n"
    assert "empty_markdown_links" in validate_export_content(bad)
