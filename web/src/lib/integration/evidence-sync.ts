/**
 * P0.4 — Explicit Evidence load/create sync. Page load never creates Evidence.
 */

import { canUseBackendApi } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";
import {
  acceptEvidence,
  createEvidence,
  fetchEvidenceList,
  fetchEvidenceSummary,
  submitEvidenceReview,
} from "@/lib/api/endpoints/evidence";
import type {
  EvidenceCreateBody,
  EvidenceDto,
  EvidenceSummaryDto,
} from "@/lib/api/types/evidence";
import {
  createsBusinessVerdictFromEvidence,
  mapBackendEvidenceToView,
} from "@/lib/integration/evidence-api-adapter";
import {
  normalizeEvidenceError,
  type EvidenceError,
} from "@/lib/integration/evidence-errors";
import { getIntegrationMode, type IntegrationMode } from "@/lib/integration/mode";
import type { EvidenceItem } from "@/lib/investigation/types";

export type EvidenceLoadResult =
  | {
      ok: true;
      mode: IntegrationMode;
      evidence: EvidenceDto[];
      views: EvidenceItem[];
      summary: EvidenceSummaryDto | null;
      createsBusinessVerdict: false;
      pageLoadSideEffect: false;
    }
  | {
      ok: false;
      mode: IntegrationMode;
      evidence: [];
      views: [];
      summary: null;
      error: EvidenceError;
      createsBusinessVerdict: false;
      pageLoadSideEffect: false;
    };

const base = {
  createsBusinessVerdict: false as const,
  pageLoadSideEffect: false as const,
};

export async function loadInvestigationEvidence(
  projectId: string,
  investigationId: string | null | undefined,
): Promise<EvidenceLoadResult> {
  const mode = getIntegrationMode();
  if (createsBusinessVerdictFromEvidence()) {
    throw new Error("evidence sync invariant broken");
  }
  if (mode === "mock" || !investigationId) {
    return { ok: true, mode, evidence: [], views: [], summary: null, ...base };
  }
  if (!canUseBackendApi()) {
    return {
      ok: false,
      mode,
      evidence: [],
      views: [],
      summary: null,
      error: normalizeEvidenceError(new ApiError("unauthorized", 401, null)),
      ...base,
    };
  }
  try {
    const [evidence, summary] = await Promise.all([
      fetchEvidenceList(projectId, investigationId),
      fetchEvidenceSummary(projectId, investigationId).catch(() => null),
    ]);
    return {
      ok: true,
      mode,
      evidence,
      views: evidence.map((e) => mapBackendEvidenceToView(e)),
      summary,
      ...base,
    };
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return { ok: true, mode, evidence: [], views: [], summary: null, ...base };
    }
    return {
      ok: false,
      mode,
      evidence: [],
      views: [],
      summary: null,
      error: normalizeEvidenceError(err),
      ...base,
    };
  }
}

export type EvidenceCreateResult =
  | {
      ok: true;
      mode: IntegrationMode;
      evidence: EvidenceDto;
      view: EvidenceItem;
      createsBusinessVerdict: false;
    }
  | {
      ok: false;
      mode: IntegrationMode;
      error: EvidenceError;
      createsBusinessVerdict: false;
    };

export async function createManualEvidence(
  projectId: string,
  investigationId: string,
  body: EvidenceCreateBody,
): Promise<EvidenceCreateResult> {
  const mode = getIntegrationMode();
  const flags = { createsBusinessVerdict: false as const };
  if (mode === "mock") {
    return {
      ok: false,
      mode,
      error: {
        kind: "unsupported_automation",
        message: "Mock mode: Evidence остаётся локальным preview.",
        status: null,
        actionHint: "Переключите hybrid/backend.",
      },
      ...flags,
    };
  }
  if (!canUseBackendApi()) {
    return {
      ok: false,
      mode,
      error: normalizeEvidenceError(new ApiError("unauthorized", 401, null)),
      ...flags,
    };
  }
  try {
    const evidence = await createEvidence(projectId, investigationId, body);
    return {
      ok: true,
      mode,
      evidence,
      view: mapBackendEvidenceToView(evidence),
      ...flags,
    };
  } catch (err) {
    return { ok: false, mode, error: normalizeEvidenceError(err), ...flags };
  }
}

export type EvidenceLifecycleResult =
  | {
      ok: true;
      mode: IntegrationMode;
      evidence: EvidenceDto;
      view: EvidenceItem;
      createsBusinessVerdict: false;
    }
  | {
      ok: false;
      mode: IntegrationMode;
      error: EvidenceError;
      createsBusinessVerdict: false;
    };

async function runEvidenceLifecycle(
  projectId: string,
  investigationId: string,
  evidenceId: string,
  action: "submit-review" | "accept",
): Promise<EvidenceLifecycleResult> {
  const mode = getIntegrationMode();
  const flags = { createsBusinessVerdict: false as const };
  if (mode === "mock") {
    return {
      ok: false,
      mode,
      error: {
        kind: "unsupported_automation",
        message: "Mock mode: Evidence lifecycle остаётся локальным.",
        status: null,
        actionHint: "Переключите hybrid/backend.",
      },
      ...flags,
    };
  }
  if (!canUseBackendApi()) {
    return {
      ok: false,
      mode,
      error: normalizeEvidenceError(new ApiError("unauthorized", 401, null)),
      ...flags,
    };
  }
  try {
    const evidence =
      action === "submit-review"
        ? await submitEvidenceReview(projectId, investigationId, evidenceId)
        : await acceptEvidence(projectId, investigationId, evidenceId);
    return {
      ok: true,
      mode,
      evidence,
      view: mapBackendEvidenceToView(evidence),
      ...flags,
    };
  } catch (err) {
    return { ok: false, mode, error: normalizeEvidenceError(err), ...flags };
  }
}

export function submitEvidenceForReview(
  projectId: string,
  investigationId: string,
  evidenceId: string,
) {
  return runEvidenceLifecycle(projectId, investigationId, evidenceId, "submit-review");
}

export function acceptEvidenceItem(
  projectId: string,
  investigationId: string,
  evidenceId: string,
) {
  return runEvidenceLifecycle(projectId, investigationId, evidenceId, "accept");
}
