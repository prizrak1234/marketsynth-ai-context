/**
 * P0.4 — Backend Evidence → Investigation Evidence view model.
 * No Finding / Business Verdict inference.
 */

import type { EvidenceDto } from "@/lib/api/types/evidence";
import type { DataOrigin } from "@/lib/integration/contracts";
import type {
  ConfidenceLevel,
  EvidenceItem,
  EvidenceState,
  InvestigationArea,
} from "@/lib/investigation/types";

const AREA_MAP: Record<string, InvestigationArea> = {
  market_research: "market",
  competitor_analysis: "competitors",
  audience_analysis: "audience",
  demand_signals: "demand",
  economics: "economics",
  risk_assessment: "risks",
  project_context: "product",
  evidence_review: "market",
  other: "market",
};

export function mapAssessmentToAlpha(state: string): EvidenceState {
  if (
    state === "confirmed" ||
    state === "partial" ||
    state === "conflicting" ||
    state === "missing" ||
    state === "outdated"
  ) {
    return state;
  }
  return "missing";
}

export function mapBackendEvidenceToView(
  dto: EvidenceDto,
  origin: DataOrigin = "backend",
): EvidenceItem & {
  originLabel: DataOrigin;
  lifecycleStatus: string;
  materiality: string;
  version: number;
  notABusinessVerdict: true;
} {
  return {
    id: dto.id,
    claim: dto.claim,
    state: mapAssessmentToAlpha(dto.assessment_state),
    supportingSourceIds: dto.source_links
      .filter((l) => l.stance === "supports")
      .map((l) => l.source_id),
    contradictingSourceIds: dto.source_links
      .filter((l) => l.stance === "contradicts")
      .map((l) => l.source_id),
    confidence:
      dto.confidence_level === "unknown"
        ? "low"
        : (dto.confidence_level as ConfidenceLevel),
    area: AREA_MAP[dto.investigation_area] ?? "market",
    reviewerNote: [
      `lifecycle: ${dto.lifecycle_status}`,
      `assessment: ${dto.assessment_state}`,
      dto.review_note ?? "",
    ]
      .filter(Boolean)
      .join(" · "),
    updatedAtLabel: dto.updated_at,
    originLabel: origin,
    lifecycleStatus: dto.lifecycle_status,
    materiality: dto.materiality,
    version: dto.version,
    notABusinessVerdict: true,
  };
}

export function createsBusinessVerdictFromEvidence(): false {
  return false;
}

export function createsFindingFromEvidence(): false {
  return false;
}
