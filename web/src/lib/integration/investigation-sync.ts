/**
 * P0.2 — Explicit Investigation create/start sync.
 * Never creates Investigation on page load. Never starts Agent Run / LLM.
 */

import { canUseBackendApi } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";
import {
  createInvestigation,
  fetchInvestigation,
  fetchLatestInvestigation,
  startInvestigation,
} from "@/lib/api/endpoints/investigations";
import { fetchLatestProjectBrief } from "@/lib/api/endpoints/project-briefs";
import type { InvestigationDto } from "@/lib/api/types/investigations";
import {
  createTriggersAgentRun,
  createTriggersLlm,
  investigationCreateBodyFromBrief,
  mapInvestigationDtoToLifecycleView,
  pageLoadCreatesInvestigation,
  type InvestigationLifecycleView,
} from "@/lib/integration/investigation-api-adapter";
import {
  normalizeInvestigationDomainError,
  type InvestigationDomainError,
} from "@/lib/integration/investigation-domain-errors";
import { reconcileInvestigationLifecycle } from "@/lib/integration/investigation-reconciliation";
import { getIntegrationMode, type IntegrationMode } from "@/lib/integration/mode";
import {
  loadInvestigationWorkspace,
  saveInvestigationWorkspace,
} from "@/lib/investigation/storage";
import type { InvestigationWorkspace } from "@/lib/investigation/types";

export type InvestigationLocalLinkMeta = {
  backendInvestigationId: string | null;
  backendInvestigationVersion: number | null;
  backendInvestigationStatus: string | null;
  linkedBriefId: string | null;
  linkedBriefVersion: number | null;
  lastInvestigationSyncAt: string | null;
};

export type InvestigationLoadDomainResult =
  | {
      ok: true;
      mode: IntegrationMode;
      investigation: InvestigationDto | null;
      view: InvestigationLifecycleView | null;
      reconciliation: ReturnType<typeof reconcileInvestigationLifecycle>;
      pageLoadSideEffect: false;
      createsAgentRun: false;
      createsLlm: false;
    }
  | {
      ok: false;
      mode: IntegrationMode;
      investigation: null;
      view: null;
      error: InvestigationDomainError;
      pageLoadSideEffect: false;
      createsAgentRun: false;
      createsLlm: false;
    };

const noSide = {
  pageLoadSideEffect: false as const,
  createsAgentRun: false as const,
  createsLlm: false as const,
};

function patchLocalLink(
  projectId: string,
  dto: InvestigationDto,
): InvestigationWorkspace | null {
  const local = loadInvestigationWorkspace(projectId);
  if (!local) return null;
  const next: InvestigationWorkspace = {
    ...local,
    status: mapInvestigationDtoToLifecycleView(dto).viewStatus,
    stages: mapInvestigationDtoToLifecycleView(dto).stages,
    lastUpdateLabel: `Backend Investigation v${dto.version} · ${dto.status}`,
    // preserve sources/evidence as local preview
  };
  saveInvestigationWorkspace(next);
  // store link in a side key via lastUpdateLabel + optional storage extension
  try {
    const key = `marketsynth.product_alpha.investigation.link.v1.${projectId}`;
    const meta: InvestigationLocalLinkMeta = {
      backendInvestigationId: dto.id,
      backendInvestigationVersion: dto.version,
      backendInvestigationStatus: dto.status,
      linkedBriefId: dto.project_brief_id,
      linkedBriefVersion: dto.project_brief_version,
      lastInvestigationSyncAt: new Date().toISOString(),
    };
    localStorage.setItem(key, JSON.stringify(meta));
  } catch {
    /* ignore */
  }
  return next;
}

export function loadInvestigationLinkMeta(
  projectId: string,
): InvestigationLocalLinkMeta | null {
  try {
    const raw = localStorage.getItem(
      `marketsynth.product_alpha.investigation.link.v1.${projectId}`,
    );
    if (!raw) return null;
    return JSON.parse(raw) as InvestigationLocalLinkMeta;
  } catch {
    return null;
  }
}

/**
 * GET-only load. Does not create or start Investigation.
 */
export async function loadInvestigationDomain(
  projectId: string,
  options?: { investigationId?: string | null },
): Promise<InvestigationLoadDomainResult> {
  const mode = getIntegrationMode();
  assert(pageLoadCreatesInvestigation() === false);
  assert(createTriggersAgentRun() === false);
  assert(createTriggersLlm() === false);

  if (mode === "mock") {
    return {
      ok: true,
      mode,
      investigation: null,
      view: null,
      reconciliation: reconcileInvestigationLifecycle({
        local: loadInvestigationWorkspace(projectId),
        backend: null,
      }),
      ...noSide,
    };
  }

  if (!canUseBackendApi()) {
    return {
      ok: false,
      mode,
      investigation: null,
      view: null,
      error: normalizeInvestigationDomainError(new ApiError("unauthorized", 401, null)),
      ...noSide,
    };
  }

  try {
    let investigation: InvestigationDto | null = null;
    if (options?.investigationId) {
      investigation = await fetchInvestigation(projectId, options.investigationId);
    } else {
      try {
        investigation = await fetchLatestInvestigation(projectId);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          investigation = null;
        } else {
          throw err;
        }
      }
    }

    const link = loadInvestigationLinkMeta(projectId);
    const local = loadInvestigationWorkspace(projectId);
    const reconciliation = reconcileInvestigationLifecycle({
      local,
      backend: investigation,
      localBackendId: link?.backendInvestigationId,
    });

    if (investigation) {
      patchLocalLink(projectId, investigation);
    }

    return {
      ok: true,
      mode,
      investigation,
      view: investigation ? mapInvestigationDtoToLifecycleView(investigation) : null,
      reconciliation,
      ...noSide,
    };
  } catch (err) {
    return {
      ok: false,
      mode,
      investigation: null,
      view: null,
      error: normalizeInvestigationDomainError(err),
      ...noSide,
    };
  }
}

export type InvestigationMutateResult =
  | {
      ok: true;
      mode: IntegrationMode;
      investigation: InvestigationDto;
      view: InvestigationLifecycleView;
      createsAgentRun: false;
      createsLlm: false;
      createsSource: false;
      createsEvidence: false;
    }
  | {
      ok: false;
      mode: IntegrationMode;
      error: InvestigationDomainError;
      createsAgentRun: false;
      createsLlm: false;
      createsSource: false;
      createsEvidence: false;
    };

const mutateBase = {
  createsAgentRun: false as const,
  createsLlm: false as const,
  createsSource: false as const,
  createsEvidence: false as const,
};

/**
 * Explicit CTA: create Investigation draft from submitted ProjectBrief.
 */
export async function createInvestigationFromSubmittedBrief(
  projectId: string,
): Promise<InvestigationMutateResult> {
  const mode = getIntegrationMode();
  if (mode === "mock") {
    return {
      ok: false,
      mode,
      error: {
        kind: "unsupported_source_domain",
        message: "Mock mode: Investigation остаётся локальным Product Alpha workspace.",
        status: null,
        actionHint: "Переключите hybrid/backend для durable Investigation.",
      },
      ...mutateBase,
    };
  }
  if (!canUseBackendApi()) {
    return {
      ok: false,
      mode,
      error: normalizeInvestigationDomainError(new ApiError("unauthorized", 401, null)),
      ...mutateBase,
    };
  }

  try {
    const brief = await fetchLatestProjectBrief(projectId);
    if (brief.status !== "submitted") {
      return {
        ok: false,
        mode,
        error: {
          kind: "brief_not_submitted",
          message: "Нужен submitted ProjectBrief.",
          status: 409,
          actionHint: "Сначала сохраните и submit полный бриф.",
        },
        ...mutateBase,
      };
    }
    const investigation = await createInvestigation(
      projectId,
      investigationCreateBodyFromBrief(brief),
    );
    patchLocalLink(projectId, investigation);
    return {
      ok: true,
      mode,
      investigation,
      view: mapInvestigationDtoToLifecycleView(investigation),
      ...mutateBase,
    };
  } catch (err) {
    return {
      ok: false,
      mode,
      error: normalizeInvestigationDomainError(err),
      ...mutateBase,
    };
  }
}

/**
 * Explicit CTA: draft/ready → active (lifecycle only).
 */
export async function startInvestigationLifecycle(
  projectId: string,
  investigationId: string,
): Promise<InvestigationMutateResult> {
  const mode = getIntegrationMode();
  if (mode === "mock") {
    return {
      ok: false,
      mode,
      error: {
        kind: "unknown_error",
        message: "Mock mode: start backend Investigation недоступен.",
        status: null,
        actionHint: "Используйте hybrid/backend.",
      },
      ...mutateBase,
    };
  }
  if (!canUseBackendApi()) {
    return {
      ok: false,
      mode,
      error: normalizeInvestigationDomainError(new ApiError("unauthorized", 401, null)),
      ...mutateBase,
    };
  }

  try {
    const investigation = await startInvestigation(projectId, investigationId);
    patchLocalLink(projectId, investigation);
    return {
      ok: true,
      mode,
      investigation,
      view: mapInvestigationDtoToLifecycleView(investigation),
      ...mutateBase,
    };
  } catch (err) {
    return {
      ok: false,
      mode,
      error: normalizeInvestigationDomainError(err),
      ...mutateBase,
    };
  }
}

function assert(cond: boolean) {
  if (!cond) throw new Error("investigation sync invariant broken");
}
