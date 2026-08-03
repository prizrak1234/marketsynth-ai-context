/**
 * Scorecard helpers for Business Verdict.
 */

import type {
  ScorecardDimension,
  ScorecardDimensionId,
  ScorecardRating,
} from "@/lib/verdict/types";

export const SCORECARD_LABELS: Record<ScorecardDimensionId, string> = {
  market_attractiveness: "Market attractiveness",
  demand_evidence: "Demand evidence",
  competitive_position: "Competitive position",
  audience_clarity: "Audience clarity",
  economic_viability: "Economic viability",
  execution_feasibility: "Execution feasibility",
  risk_exposure: "Risk exposure",
  evidence_quality: "Evidence quality",
};

export function dim(
  id: ScorecardDimensionId,
  rating: ScorecardRating,
  explanation: string,
  evidenceIds: string[],
  criticalGap?: string,
): ScorecardDimension {
  return {
    id,
    label: SCORECARD_LABELS[id],
    rating,
    explanation,
    evidenceIds,
    criticalGap,
  };
}

/** Secondary deterministic summary — qualitative decision remains primary */
export function scorecardSummaryIndex(dimensions: ScorecardDimension[]): number {
  const weight: Record<ScorecardRating, number> = {
    strong: 4,
    acceptable: 3,
    weak: 1,
    critical: 0,
    insufficient_data: 0,
  };
  if (dimensions.length === 0) return 0;
  const sum = dimensions.reduce((acc, d) => acc + weight[d.rating], 0);
  return Math.round((sum / (dimensions.length * 4)) * 100);
}
