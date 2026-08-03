"""Safe audit logging for campaign supervisor reports (Phase AI.253)."""

from __future__ import annotations

from app.core.logging import get_logger
from app.schemas.contracts import CampaignSupervisorReport, CampaignSupervisorSeverity

log = get_logger(__name__)


def log_campaign_supervisor_report(
    *,
    campaign_id: str,
    project_id: str,
    report: CampaignSupervisorReport,
) -> None:
    critical_count = sum(
        1 for item in report.findings if item.severity == CampaignSupervisorSeverity.CRITICAL
    )
    log.info(
        "campaign_supervisor_report_audit",
        campaign_id=campaign_id,
        project_id=project_id,
        report_generated=True,
        findings_count=len(report.findings),
        critical_count=critical_count,
        health_score=report.health_score,
        missing_inputs_count=len(report.missing_inputs),
        contradictions_count=len(report.contradictions),
        risks_count=len(report.risks),
    )
