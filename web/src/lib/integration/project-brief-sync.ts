/**
 * P0.1 — Explicit ProductIntakeDraft → ProjectBrief sync.
 * Never auto-uploads on page load. Mock mode unchanged.
 */

import { canUseBackendApi } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";
import {
  createProjectBrief,
  fetchLatestProjectBrief,
  fetchProjectBriefs,
  submitProjectBrief,
  updateProjectBrief,
} from "@/lib/api/endpoints/project-briefs";
import type { ProjectBriefDto } from "@/lib/api/types/project-briefs";
import {
  detectBriefFieldLoss,
  mapIntakeDraftToBriefCreate,
} from "@/lib/integration/project-brief-adapter";
import {
  normalizeProjectBriefError,
  type ProjectBriefError,
} from "@/lib/integration/project-brief-errors";
import {
  reconcileBriefFingerprints,
  type BriefReconciliationResult,
} from "@/lib/integration/project-brief-reconciliation";
import { getIntegrationMode, type IntegrationMode } from "@/lib/integration/mode";
import { evaluateIntakeReadiness } from "@/lib/project-intake/readiness";
import { saveIntakeDraft, saveLinkedIntakeDraft } from "@/lib/project-intake/storage";
import type {
  IntakeBriefSyncMeta,
  ProjectIntakeDraft,
} from "@/lib/project-intake/types";

export type BriefSyncResult =
  | {
      ok: true;
      mode: IntegrationMode;
      draft: ProjectIntakeDraft;
      brief: ProjectBriefDto;
      submitted: boolean;
      fieldLoss: ReturnType<typeof detectBriefFieldLoss>;
      createsInvestigation: false;
      createsAgentRun: false;
    }
  | {
      ok: false;
      mode: IntegrationMode;
      draft: ProjectIntakeDraft;
      error: ProjectBriefError;
      reconciliation?: BriefReconciliationResult;
      createsInvestigation: false;
      createsAgentRun: false;
    };

function persist(draft: ProjectIntakeDraft): ProjectIntakeDraft {
  saveIntakeDraft(draft);
  const pid = draft.backendSync?.backendProjectId;
  if (pid) saveLinkedIntakeDraft(pid, draft);
  return draft;
}

function withBriefMeta(
  draft: ProjectIntakeDraft,
  patch: Partial<IntakeBriefSyncMeta>,
): ProjectIntakeDraft {
  const prev = draft.briefSync ?? {
    backendBriefId: null,
    backendBriefVersion: null,
    backendBriefStatus: null,
    backendBriefFingerprint: null,
    briefSyncState: "not_linked" as const,
    lastBriefSyncAt: null,
    lastBriefSyncError: null,
  };
  return {
    ...draft,
    briefSync: { ...prev, ...patch },
    updatedAt: new Date().toISOString(),
  };
}

/**
 * Explicit user action: save full brief to Marketsynth backend.
 * Requires existing backend Project link (I2). Optionally submit.
 */
export async function syncIntakeBrief(
  draft: ProjectIntakeDraft,
  options: { submit?: boolean } = {},
): Promise<BriefSyncResult> {
  const mode = getIntegrationMode();
  const fieldLoss = detectBriefFieldLoss(draft);
  const baseFail = {
    createsInvestigation: false as const,
    createsAgentRun: false as const,
  };

  if (mode === "mock") {
    return {
      ok: false,
      mode,
      draft,
      error: {
        kind: "migration_blocked",
        message: "Mock mode: полный бриф остаётся локально (без backend).",
        status: null,
        actionHint: "Переключите режим hybrid/backend для ProjectBrief.",
      },
      ...baseFail,
    };
  }

  if (!canUseBackendApi()) {
    return {
      ok: false,
      mode,
      draft: persist(
        withBriefMeta(draft, {
          briefSyncState: "failed",
          lastBriefSyncError: "API key missing",
        }),
      ),
      error: normalizeProjectBriefError(new ApiError("unauthorized", 401, null)),
      ...baseFail,
    };
  }

  const projectId = draft.backendSync?.backendProjectId;
  if (!projectId) {
    return {
      ok: false,
      mode,
      draft,
      error: {
        kind: "project_required",
        message: "Сначала сохраните ядро Project.",
        status: null,
        actionHint: "Используйте CTA Project sync, затем сохраните полный бриф.",
      },
      ...baseFail,
    };
  }

  const withReady: ProjectIntakeDraft = {
    ...draft,
    readiness: draft.readiness ?? evaluateIntakeReadiness(draft),
  };
  const body = mapIntakeDraftToBriefCreate(withReady);

  try {
    let brief: ProjectBriefDto | null = null;
    const linkedId = withReady.briefSync?.backendBriefId;

    if (linkedId && withReady.briefSync?.backendBriefStatus === "draft") {
      brief = await updateProjectBrief(projectId, linkedId, body);
    } else {
      try {
        brief = await createProjectBrief(projectId, body);
      } catch (err) {
        // existing open draft → update it
        if (err instanceof ApiError && err.status === 409) {
          const drafts = await fetchProjectBriefs(projectId, { status: "draft", limit: 1 });
          if (drafts[0]) {
            brief = await updateProjectBrief(projectId, drafts[0].id, body);
          } else {
            throw err;
          }
        } else {
          throw err;
        }
      }
    }

    let submitted = false;
    if (options.submit && brief) {
      brief = await submitProjectBrief(projectId, brief.id);
      submitted = true;
    }

    const next = persist(
      withBriefMeta(withReady, {
        backendBriefId: brief.id,
        backendBriefVersion: brief.version,
        backendBriefStatus: brief.status,
        backendBriefFingerprint: brief.input_fingerprint,
        briefSyncState: submitted ? "submitted" : "draft_saved",
        lastBriefSyncAt: new Date().toISOString(),
        lastBriefSyncError: null,
      }),
    );

    return {
      ok: true,
      mode,
      draft: next,
      brief,
      submitted,
      fieldLoss,
      ...baseFail,
    };
  } catch (err) {
    const error = normalizeProjectBriefError(err);
    return {
      ok: false,
      mode,
      draft: persist(
        withBriefMeta(withReady, {
          briefSyncState: "failed",
          lastBriefSyncError: error.message,
        }),
      ),
      error,
      ...baseFail,
    };
  }
}

export async function inspectBriefReconciliation(
  draft: ProjectIntakeDraft,
): Promise<BriefReconciliationResult | null> {
  const mode = getIntegrationMode();
  if (mode === "mock") return null;
  const projectId = draft.backendSync?.backendProjectId;
  if (!projectId || !canUseBackendApi()) return null;
  try {
    const backend = await fetchLatestProjectBrief(projectId);
    return reconcileBriefFingerprints({
      localFingerprint: draft.briefSync?.backendBriefFingerprint ?? null,
      backend,
      localUpdatedAt: draft.updatedAt,
    });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return reconcileBriefFingerprints({
        localFingerprint: draft.briefSync?.backendBriefFingerprint ?? null,
        backend: null,
        localUpdatedAt: draft.updatedAt,
      });
    }
    return null;
  }
}
