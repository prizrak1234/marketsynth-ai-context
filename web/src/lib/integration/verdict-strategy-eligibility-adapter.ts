/**
 * P0.5 — Strategy eligibility from durable BusinessVerdict (eligibility only).
 */

import type { BackendVerdictDto } from "@/lib/api/types/business-verdicts";
import type { StrategyEligibilityResult } from "@/lib/integration/strategy-eligibility";
import { resolveStrategyEligibility } from "@/lib/integration/strategy-eligibility";
import type { BusinessVerdictType, VerdictStatus } from "@/lib/verdict/types";

const TYPE_MAP: Record<string, BusinessVerdictType> = {
  go: "GO",
  conditional_go: "CONDITIONAL_GO",
  no_go: "NO_GO",
  insufficient_data: "INSUFFICIENT_DATA",
};

function mapStatus(lifecycle: string): VerdictStatus {
  if (lifecycle === "approved") return "approved";
  if (lifecycle === "under_review") return "under_review";
  if (lifecycle === "superseded") return "superseded";
  return "draft";
}

export function mapBackendStrategyEligibility(
  dto: BackendVerdictDto,
): StrategyEligibilityResult {
  const base = resolveStrategyEligibility({
    verdictType: TYPE_MAP[dto.verdict_type] ?? null,
    verdictStatus: mapStatus(dto.lifecycle_status),
    origin: {
      origin: "backend",
      authority:
        dto.lifecycle_status === "approved"
          ? "backend_approved"
          : "backend_draft",
      labelRu: "Backend BusinessVerdict",
      labelEn: "Backend BusinessVerdict",
      evidenceBasis: "durable_evidence_sot",
      persistedToBackend: true,
      evidenceVerified: true,
    },
    readinessStatus: null,
  });
  // Firewall: never claim Strategy creation
  return {
    ...base,
    createsExecutionApproval: false,
    generatesStrategyBackend: false,
  };
}
