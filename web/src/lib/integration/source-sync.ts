/**
 * P0.3 — Explicit Source registration/load sync.
 * Page load never registers Sources. No URL fetch. No Evidence.
 */

import { canUseBackendApi } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";
import {
  attachSourceToInvestigation,
  fetchInvestigationSources,
  fetchProjectSources,
  registerSource,
} from "@/lib/api/endpoints/sources";
import type { SourceCreateBody, SourceDto } from "@/lib/api/types/sources";
import {
  createsEvidenceFromSource,
  fetchesUrlOnRegister,
  mapBackendSourceToView,
} from "@/lib/integration/source-api-adapter";
import {
  normalizeSourceError,
  type SourceError,
} from "@/lib/integration/source-errors";
import { getIntegrationMode, type IntegrationMode } from "@/lib/integration/mode";
import type { InvestigationSource } from "@/lib/investigation/types";

export type SourceLoadResult =
  | {
      ok: true;
      mode: IntegrationMode;
      sources: SourceDto[];
      views: InvestigationSource[];
      createsEvidence: false;
      fetchesUrl: false;
      pageLoadSideEffect: false;
    }
  | {
      ok: false;
      mode: IntegrationMode;
      sources: [];
      views: [];
      error: SourceError;
      createsEvidence: false;
      fetchesUrl: false;
      pageLoadSideEffect: false;
    };

const base = {
  createsEvidence: false as const,
  fetchesUrl: false as const,
  pageLoadSideEffect: false as const,
};

export async function loadProjectSources(projectId: string): Promise<SourceLoadResult> {
  const mode = getIntegrationMode();
  if (createsEvidenceFromSource() || fetchesUrlOnRegister()) {
    throw new Error("source sync invariant broken");
  }
  if (mode === "mock") {
    return { ok: true, mode, sources: [], views: [], ...base };
  }
  if (!canUseBackendApi()) {
    return {
      ok: false,
      mode,
      sources: [],
      views: [],
      error: normalizeSourceError(new ApiError("unauthorized", 401, null)),
      ...base,
    };
  }
  try {
    const sources = await fetchProjectSources(projectId, {
      status: undefined,
      limit: 50,
    });
    const live = sources.filter(
      (s) => s.status !== "superseded" && s.status !== "archived",
    );
    return {
      ok: true,
      mode,
      sources: live,
      views: live.map((s) => mapBackendSourceToView(s)),
      ...base,
    };
  } catch (err) {
    return {
      ok: false,
      mode,
      sources: [],
      views: [],
      error: normalizeSourceError(err),
      ...base,
    };
  }
}

export async function loadInvestigationLinkedSources(
  projectId: string,
  investigationId: string,
): Promise<SourceLoadResult> {
  const mode = getIntegrationMode();
  if (mode === "mock") {
    return { ok: true, mode, sources: [], views: [], ...base };
  }
  if (!canUseBackendApi()) {
    return {
      ok: false,
      mode,
      sources: [],
      views: [],
      error: normalizeSourceError(new ApiError("unauthorized", 401, null)),
      ...base,
    };
  }
  try {
    const items = await fetchInvestigationSources(projectId, investigationId, {
      status: "accepted",
      limit: 50,
    });
    const sources = items.map((i) => i.source);
    return {
      ok: true,
      mode,
      sources,
      views: sources.map((s) => mapBackendSourceToView(s)),
      ...base,
    };
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return { ok: true, mode, sources: [], views: [], ...base };
    }
    return {
      ok: false,
      mode,
      sources: [],
      views: [],
      error: normalizeSourceError(err),
      ...base,
    };
  }
}

export type SourceRegisterResult =
  | {
      ok: true;
      mode: IntegrationMode;
      source: SourceDto;
      view: InvestigationSource;
      createsEvidence: false;
      fetchesUrl: false;
    }
  | {
      ok: false;
      mode: IntegrationMode;
      error: SourceError;
      createsEvidence: false;
      fetchesUrl: false;
    };

export async function registerProjectSource(
  projectId: string,
  body: SourceCreateBody,
  options?: { investigationId?: string | null },
): Promise<SourceRegisterResult> {
  const mode = getIntegrationMode();
  const flags = { createsEvidence: false as const, fetchesUrl: false as const };
  if (mode === "mock") {
    return {
      ok: false,
      mode,
      error: {
        kind: "unsupported_fetch",
        message: "Mock mode: Source остаётся локальным Product Alpha preview.",
        status: null,
        actionHint: "Переключите hybrid/backend для durable Source.",
      },
      ...flags,
    };
  }
  if (!canUseBackendApi()) {
    return {
      ok: false,
      mode,
      error: normalizeSourceError(new ApiError("unauthorized", 401, null)),
      ...flags,
    };
  }
  try {
    const payload: SourceCreateBody = {
      ...body,
      attach_to_investigation_id: options?.investigationId ?? body.attach_to_investigation_id,
    };
    const source = await registerSource(projectId, payload);
    if (options?.investigationId && !payload.attach_to_investigation_id) {
      await attachSourceToInvestigation(projectId, options.investigationId, source.id, {
        status: "accepted",
      });
    }
    return {
      ok: true,
      mode,
      source,
      view: mapBackendSourceToView(source),
      ...flags,
    };
  } catch (err) {
    return { ok: false, mode, error: normalizeSourceError(err), ...flags };
  }
}
