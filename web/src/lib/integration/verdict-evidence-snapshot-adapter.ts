/**
 * P0.5 — Evidence snapshot adapter for Verdict Workspace.
 */

import type { BackendEvidenceSnapshotDto } from "@/lib/api/types/business-verdicts";

export type VerdictEvidenceSnapshotView = {
  id: string;
  snapshotHash: string;
  acceptedCount: number;
  missingCritical: number;
  conflictingCritical: number;
  outdatedCritical: number;
  readinessStatus: string;
  readinessContribution: string;
  areaCoverage: Record<string, number>;
  evidenceCount: number;
  disclaimer: string;
};

export function mapEvidenceSnapshotView(
  dto: BackendEvidenceSnapshotDto,
): VerdictEvidenceSnapshotView {
  return {
    id: dto.id,
    snapshotHash: dto.snapshot_hash,
    acceptedCount: dto.accepted_evidence_count,
    missingCritical: dto.missing_critical_count,
    conflictingCritical: dto.conflicting_critical_count,
    outdatedCritical: dto.outdated_critical_count,
    readinessStatus: dto.readiness_status,
    readinessContribution: dto.verdict_readiness_contribution,
    areaCoverage: dto.area_coverage || {},
    evidenceCount: (dto.evidence_ids || []).length,
    disclaimer:
      "Immutable Evidence Snapshot — не live-query. Поздние изменения Evidence не переписывают этот вердикт.",
  };
}
