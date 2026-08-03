/** P0.6 — Strategy ↔ Verdict link view. */

import type { BackendMarketingStrategyDto } from "@/lib/api/types/marketing-strategies";

export type StrategyVerdictLinkView = {
  verdictId: string;
  verdictVersion: number;
  verdictType: string;
  evidenceSnapshotId: string;
  evidenceSnapshotHash: string;
  conditionsPreserved: number;
  disclaimer: string;
};

export function mapStrategyVerdictLink(
  dto: BackendMarketingStrategyDto,
): StrategyVerdictLinkView {
  return {
    verdictId: dto.business_verdict_id,
    verdictVersion: dto.business_verdict_version,
    verdictType: dto.business_verdict_type,
    evidenceSnapshotId: dto.evidence_snapshot_id,
    evidenceSnapshotHash: dto.evidence_snapshot_hash,
    conditionsPreserved: (dto.verdict_conditions || []).length,
    disclaimer:
      "Verdict conditions remain authoritative in BusinessVerdict domain — Strategy only references them.",
  };
}
