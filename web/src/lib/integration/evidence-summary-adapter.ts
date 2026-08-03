/**
 * P0.4 — Evidence summary → readiness contribution view (not Business Verdict).
 */

import type { EvidenceSummaryDto } from "@/lib/api/types/evidence";

export type EvidenceSummaryView = {
  total: number;
  acceptedCount: number;
  missingCritical: number;
  conflictingCritical: number;
  outdatedCritical: number;
  readinessContribution: "sufficient" | "partial" | "blocked";
  notABusinessVerdict: true;
  notice: string;
};

export function mapEvidenceSummary(dto: EvidenceSummaryDto): EvidenceSummaryView {
  const readiness =
    dto.verdict_readiness_contribution === "sufficient" ||
    dto.verdict_readiness_contribution === "blocked"
      ? dto.verdict_readiness_contribution
      : "partial";
  return {
    total: dto.total,
    acceptedCount: dto.accepted_count,
    missingCritical: dto.missing_critical_claims,
    conflictingCritical: dto.conflicting_critical_claims,
    outdatedCritical: dto.outdated_critical_claims,
    readinessContribution: readiness,
    notABusinessVerdict: true,
    notice:
      "Evidence summary feeds Verdict Readiness inputs only. Business Verdict is P0.5.",
  };
}
