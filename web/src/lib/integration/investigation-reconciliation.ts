/**
 * P0.2 — Local Investigation workspace ↔ backend lifecycle reconciliation.
 * Backend wins for lifecycle fields. Local Source/Evidence remain separate preview.
 */

import type { InvestigationDto } from "@/lib/api/types/investigations";
import type { InvestigationStageId, InvestigationWorkspace } from "@/lib/investigation/types";

export type InvestigationReconciliationKind =
  | "aligned"
  | "local_only"
  | "backend_only"
  | "lifecycle_conflict"
  | "stage_conflict";

export type InvestigationReconciliationResult = {
  kind: InvestigationReconciliationKind;
  backendWinsLifecycle: true;
  localArtifactsSeparate: true;
  message: string;
  backendInvestigationId: string | null;
  backendVersion: number | null;
  backendStatus: string | null;
  backendCurrentStage: InvestigationStageId | null;
  localCurrentStage: InvestigationStageId | null;
};

function localCurrentStage(
  ws: InvestigationWorkspace | null,
): InvestigationStageId | null {
  if (!ws) return null;
  const active = ws.stages.find(
    (s) => s.state === "in_progress" || s.state === "queued",
  );
  return (active?.id as InvestigationStageId) ?? ws.stages[0]?.id ?? null;
}

export function reconcileInvestigationLifecycle(args: {
  local: InvestigationWorkspace | null;
  backend: InvestigationDto | null;
  localBackendId?: string | null;
}): InvestigationReconciliationResult {
  const { local, backend, localBackendId } = args;
  const localStage = localCurrentStage(local);

  if (!backend && !local) {
    return {
      kind: "aligned",
      backendWinsLifecycle: true,
      localArtifactsSeparate: true,
      message: "Нет локального preview и нет backend Investigation.",
      backendInvestigationId: null,
      backendVersion: null,
      backendStatus: null,
      backendCurrentStage: null,
      localCurrentStage: null,
    };
  }

  if (!backend) {
    return {
      kind: "local_only",
      backendWinsLifecycle: true,
      localArtifactsSeparate: true,
      message: "Локальный preview без backend Investigation (mock/hybrid artifacts).",
      backendInvestigationId: localBackendId ?? null,
      backendVersion: null,
      backendStatus: null,
      backendCurrentStage: null,
      localCurrentStage: localStage,
    };
  }

  if (!local) {
    return {
      kind: "backend_only",
      backendWinsLifecycle: true,
      localArtifactsSeparate: true,
      message: "Backend Investigation — SoT; локальных артефактов нет.",
      backendInvestigationId: backend.id,
      backendVersion: backend.version,
      backendStatus: backend.status,
      backendCurrentStage: backend.current_stage as InvestigationStageId,
      localCurrentStage: null,
    };
  }

  const linked = localBackendId && localBackendId === backend.id;
  const stageDiffers =
    localStage != null && localStage !== (backend.current_stage as InvestigationStageId);

  if (linked && stageDiffers) {
    return {
      kind: "stage_conflict",
      backendWinsLifecycle: true,
      localArtifactsSeparate: true,
      message:
        "Локальный current stage отличается от backend. Backend lifecycle побеждает; Source/Evidence local preview не перезаписываются.",
      backendInvestigationId: backend.id,
      backendVersion: backend.version,
      backendStatus: backend.status,
      backendCurrentStage: backend.current_stage as InvestigationStageId,
      localCurrentStage: localStage,
    };
  }

  if (localBackendId && localBackendId !== backend.id) {
    return {
      kind: "lifecycle_conflict",
      backendWinsLifecycle: true,
      localArtifactsSeparate: true,
      message: "Локальная связка Investigation ID не совпадает с latest backend.",
      backendInvestigationId: backend.id,
      backendVersion: backend.version,
      backendStatus: backend.status,
      backendCurrentStage: backend.current_stage as InvestigationStageId,
      localCurrentStage: localStage,
    };
  }

  return {
    kind: "aligned",
    backendWinsLifecycle: true,
    localArtifactsSeparate: true,
    message: "Lifecycle согласован; Source/Evidence остаются отдельным preview.",
    backendInvestigationId: backend.id,
    backendVersion: backend.version,
    backendStatus: backend.status,
    backendCurrentStage: backend.current_stage as InvestigationStageId,
    localCurrentStage: localStage,
  };
}
