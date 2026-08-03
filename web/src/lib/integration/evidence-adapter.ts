/**
 * I3 — Evidence / findings semantic firewall.
 *
 * Supervisor Finding ≠ Evidence
 * LLM response ≠ Evidence
 * Skill output ≠ Evidence
 * Task output ≠ Evidence
 *
 * Adapters may surface quality signals with explicit roles only.
 */

import type {
  CampaignSupervisorFinding,
  CampaignSupervisorReport,
} from "@/lib/api/types/business-campaigns";
import type { DataOrigin } from "@/lib/integration/contracts";

export type QualitySignalRole =
  | "campaign_quality_finding"
  | "campaign_missing_input"
  | "campaign_contradiction_string"
  | "campaign_risk_string";

export type QualitySignalView = {
  id: string;
  role: QualitySignalRole;
  title: string;
  description: string;
  severity: string;
  category: string | null;
  origin: DataOrigin;
  disclaimer: string;
};

const NOT_EVIDENCE =
  "Не является Investigation Evidence. Campaign quality signal only.";

export function mapSupervisorFindingToQualitySignal(
  finding: CampaignSupervisorFinding,
  index: number,
): QualitySignalView {
  return {
    id: `sup_finding_${index}_${finding.title.slice(0, 24)}`,
    role: "campaign_quality_finding",
    title: finding.title,
    description: finding.description,
    severity: finding.severity,
    category: finding.category,
    origin: "backend",
    disclaimer: NOT_EVIDENCE,
  };
}

export function mapSupervisorReportToQualitySignals(
  report: CampaignSupervisorReport | null,
): QualitySignalView[] {
  if (!report) return [];
  const out: QualitySignalView[] = [];
  report.findings.forEach((f, i) => out.push(mapSupervisorFindingToQualitySignal(f, i)));
  report.missing_inputs.forEach((m, i) => {
    out.push({
      id: `sup_missing_${i}`,
      role: "campaign_missing_input",
      title: "Campaign missing input",
      description: m,
      severity: "warning",
      category: "brief",
      origin: "backend",
      disclaimer: "Missing brief/campaign input — не MissingDataItem Investigation.",
    });
  });
  report.contradictions.forEach((c, i) => {
    out.push({
      id: `sup_contradiction_${i}`,
      role: "campaign_contradiction_string",
      title: "Campaign contradiction (string)",
      description: c,
      severity: "warning",
      category: null,
      origin: "backend",
      disclaimer: "Не ContradictionItem с evidence links / resolution workflow.",
    });
  });
  report.risks.forEach((r, i) => {
    out.push({
      id: `sup_risk_${i}`,
      role: "campaign_risk_string",
      title: "Campaign risk (string)",
      description: r,
      severity: "warning",
      category: null,
      origin: "backend",
      disclaimer: "Не RiskItem Investigation (нет severity/probability/evidence).",
    });
  });
  return out;
}

/** Hard rule: never auto-build EvidenceItem from quality signals. */
export function qualitySignalsAreNotEvidence(): true {
  return true;
}
