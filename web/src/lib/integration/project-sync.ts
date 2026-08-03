/**
 * I2 Project sync — create/update existing backend Project from intake.
 * Full ProductIntakeDraft stays local; only supported core is persisted.
 */

import {
  createProject,
  fetchProject,
  fetchProjects,
  updateProject,
  type Project,
} from "@/lib/api/endpoints/projects";
import { canUseBackendApi } from "@/lib/api/config";
import {
  buildSubmissionFingerprint,
  mapIntakeToProjectCreate,
  mapIntakeToProjectUpdate,
  readConfigPointer,
} from "@/lib/integration/intake-project-mapping";
import { getIntegrationMode, type IntegrationMode } from "@/lib/integration/mode";
import {
  ambiguousCreateError,
  normalizeProjectWriteError,
  type ProjectWriteError,
} from "@/lib/integration/project-write-adapter";
import { createMockProjectFromDraft } from "@/lib/project-intake/mock-project";
import {
  clearIntakeDraft,
  saveIntakeDraft,
  saveLinkedIntakeDraft,
} from "@/lib/project-intake/storage";
import type {
  IntakeBackendSyncMeta,
  IntakeBackendSyncState,
  ProjectIntakeDraft,
} from "@/lib/project-intake/types";

export type ProjectSyncResult =
  | {
      ok: true;
      mode: IntegrationMode;
      projectId: string;
      origin: "mock" | "backend";
      draft: ProjectIntakeDraft;
      investigationMockOnly: true;
      sectionsPersisted: string[];
      sectionsLocalOnly: string[];
    }
  | {
      ok: false;
      mode: IntegrationMode;
      draft: ProjectIntakeDraft;
      error: ProjectWriteError;
      investigationMockOnly: true;
    };

/** In-memory lock — prevents double-click duplicate POST/PATCH. */
let syncInFlightDraftId: string | null = null;

export function isProjectSyncInFlight(draftId: string): boolean {
  return syncInFlightDraftId === draftId;
}

function withSyncMeta(
  draft: ProjectIntakeDraft,
  patch: Partial<IntakeBackendSyncMeta>,
): ProjectIntakeDraft {
  const prev = draft.backendSync ?? {
    backendProjectId: null,
    backendSyncState: "local_only" as IntakeBackendSyncState,
    backendSyncedAt: null,
    backendUpdatedAt: null,
    lastSyncError: null,
    submissionFingerprint: null,
    localDraftVersion: draft.updatedAt,
  };
  return {
    ...draft,
    backendSync: {
      ...prev,
      localDraftVersion: draft.updatedAt,
      ...patch,
    },
    updatedAt: new Date().toISOString(),
  };
}

function persistLocal(draft: ProjectIntakeDraft): ProjectIntakeDraft {
  saveIntakeDraft(draft);
  const pid = draft.backendSync?.backendProjectId;
  if (pid) saveLinkedIntakeDraft(pid, draft);
  return draft;
}

const SECTIONS_PERSISTED = [
  "projectBasics.name → Project.name",
  "idea/product short text → Project.description",
  "config.marketsynth_i2 pointer (draft correlation only)",
];

const SECTIONS_LOCAL = [
  "полный ProductIntakeDraft",
  "market / audience / economics",
  "materials (mock metadata only)",
  "assumptions / missingData / readiness",
  "Investigation (не подключено)",
];

function bindSyncedProject(
  draft: ProjectIntakeDraft,
  project: Project,
  fingerprint: string,
): ProjectIntakeDraft {
  const now = new Date().toISOString();
  return persistLocal(
    withSyncMeta(draft, {
      backendProjectId: project.id,
      backendSyncState: "partially_synced",
      backendSyncedAt: now,
      backendUpdatedAt: project.updated_at,
      lastSyncError: null,
      submissionFingerprint: fingerprint,
    }),
  );
}

export type BackendProjectIdentityResolution =
  | { kind: "existing"; project: Project }
  | { kind: "reconciled"; project: Project; staleProjectId: string }
  | { kind: "created"; project: Project };

/**
 * Resolve canonical backend Project for intake draft.
 * Stale backendProjectId → reconcile by draft pointer → create once (no duplicate POST on network ambiguity).
 */
export async function resolveIntakeBackendProjectIdentity(
  draft: ProjectIntakeDraft,
  fingerprint: string,
): Promise<
  | { ok: true; resolution: BackendProjectIdentityResolution; draft: ProjectIntakeDraft }
  | { ok: false; draft: ProjectIntakeDraft; error: ProjectWriteError }
> {
  let working = draft;
  const staleId = working.backendSync?.backendProjectId;

  async function updateExisting(project: Project): Promise<Project> {
    return updateProject(
      project.id,
      mapIntakeToProjectUpdate(working, fingerprint, project.config),
    );
  }

  if (staleId) {
    try {
      const existing = await fetchProject(staleId);
      const project = await updateExisting(existing);
      return {
        ok: true,
        resolution: { kind: "existing", project },
        draft: bindSyncedProject(working, project, fingerprint),
      };
    } catch (err) {
      const normalized = normalizeProjectWriteError(err);
      if (normalized.kind !== "project_not_found") {
        const failed = persistLocal(
          withSyncMeta(working, {
            backendSyncState: "failed",
            lastSyncError: normalized.message,
          }),
        );
        return { ok: false, draft: failed, error: normalized };
      }

      const reconciled = await tryReconcileByDraftId(working.id);
      if (reconciled) {
        const project = await updateExisting(reconciled);
        return {
          ok: true,
          resolution: { kind: "reconciled", project, staleProjectId: staleId },
          draft: bindSyncedProject(working, project, fingerprint),
        };
      }

      working = persistLocal(
        withSyncMeta(working, {
          backendProjectId: null,
          backendSyncState: "creating",
          lastSyncError: null,
        }),
      );
    }
  }

  try {
    const created = await createProject(mapIntakeToProjectCreate(working));
    const project = await updateExisting(created);
    return {
      ok: true,
      resolution: { kind: "created", project },
      draft: bindSyncedProject(working, project, fingerprint),
    };
  } catch (err) {
    const normalized = normalizeProjectWriteError(err);
    if (normalized.kind === "network_error") {
      const reconciled = await tryReconcileByDraftId(working.id);
      if (reconciled) {
        const project = await updateExisting(reconciled);
        return {
          ok: true,
          resolution: {
            kind: "reconciled",
            project,
            staleProjectId: staleId ?? "network_ambiguous",
          },
          draft: bindSyncedProject(working, project, fingerprint),
        };
      }
      const failed = persistLocal(
        withSyncMeta(working, {
          backendSyncState: "conflict",
          lastSyncError: ambiguousCreateError().message,
        }),
      );
      return { ok: false, draft: failed, error: ambiguousCreateError() };
    }

    const failed = persistLocal(
      withSyncMeta(working, {
        backendSyncState: "failed",
        lastSyncError: normalized.message,
      }),
    );
    return { ok: false, draft: failed, error: normalized };
  }
}

function successResult(
  mode: IntegrationMode,
  projectId: string,
  draft: ProjectIntakeDraft,
  origin: "mock" | "backend",
): ProjectSyncResult {
  return {
    ok: true,
    mode,
    projectId,
    origin,
    draft,
    investigationMockOnly: true,
    sectionsPersisted: origin === "backend" ? SECTIONS_PERSISTED : [],
    sectionsLocalOnly: origin === "backend" ? SECTIONS_LOCAL : ["весь черновик + mock project (localStorage)"],
  };
}

/** Safe reconcile: list projects and match config pointer — no POST. */
export async function tryReconcileByDraftId(localDraftId: string): Promise<Project | null> {
  try {
    const projects = await fetchProjects();
    for (const p of projects) {
      const pointer = readConfigPointer(p.config);
      if (pointer?.localDraftId === localDraftId) return p;
    }
  } catch {
    /* ignore — still ambiguous */
  }
  return null;
}

export async function syncIntakeProject(draft: ProjectIntakeDraft): Promise<ProjectSyncResult> {
  const mode = getIntegrationMode();

  if (mode === "mock") {
    const project = createMockProjectFromDraft(draft);
    clearIntakeDraft();
    return successResult(mode, project.id, draft, "mock");
  }

  // backend | hybrid — never silent mock fallback
  if (!canUseBackendApi()) {
    const failed = persistLocal(
      withSyncMeta(draft, {
        backendSyncState: "failed",
        lastSyncError: "Требуется API key.",
      }),
    );
    return {
      ok: false,
      mode,
      draft: failed,
      error: {
        kind: "unauthorized",
        message: "Требуется API key для режима backend/hybrid.",
        status: 401,
        actionHint: "Укажите ключ и повторите. Mock-fallback отключён.",
      },
      investigationMockOnly: true,
    };
  }

  if (syncInFlightDraftId === draft.id) {
    return {
      ok: false,
      mode,
      draft,
      error: {
        kind: "conflict",
        message: "Сохранение уже выполняется.",
        status: null,
        actionHint: "Дождитесь завершения текущего запроса.",
      },
      investigationMockOnly: true,
    };
  }

  const sync = draft.backendSync;
  if (sync?.backendSyncState === "conflict" && sync.lastSyncError?.includes("ambiguous")) {
    return {
      ok: false,
      mode,
      draft,
      error: ambiguousCreateError(),
      investigationMockOnly: true,
    };
  }

  const fingerprint = buildSubmissionFingerprint(draft);

  const alreadyLinked =
    sync?.backendProjectId &&
    (sync.backendSyncState === "synced" || sync.backendSyncState === "partially_synced") &&
    sync.submissionFingerprint === fingerprint;

  if (alreadyLinked && sync.backendProjectId) {
    try {
      await fetchProject(sync.backendProjectId);
      return successResult(mode, sync.backendProjectId, draft, "backend");
    } catch {
      /* stale backendProjectId — fall through and re-sync */
    }
  }

  syncInFlightDraftId = draft.id;
  let working = persistLocal(
    withSyncMeta(draft, {
      backendSyncState: sync?.backendProjectId ? "update_pending" : "creating",
      submissionFingerprint: fingerprint,
      lastSyncError: null,
    }),
  );

  try {
    const resolved = await resolveIntakeBackendProjectIdentity(working, fingerprint);
    if (!resolved.ok) {
      return {
        ok: false,
        mode,
        draft: resolved.draft,
        error: resolved.error,
        investigationMockOnly: true,
      };
    }

    try {
      await fetchProject(resolved.resolution.project.id);
    } catch (err) {
      const n = normalizeProjectWriteError(err);
      const failed = persistLocal(
        withSyncMeta(resolved.draft, {
          backendSyncState: "failed",
          lastSyncError: n.message,
        }),
      );
      return { ok: false, mode, draft: failed, error: n, investigationMockOnly: true };
    }

    return successResult(mode, resolved.resolution.project.id, resolved.draft, "backend");
  } catch (err) {
    const n = normalizeProjectWriteError(err);
    working = persistLocal(
      withSyncMeta(working, {
        backendSyncState: "failed",
        lastSyncError: n.message,
      }),
    );
    return { ok: false, mode, draft: working, error: n, investigationMockOnly: true };
  } finally {
    syncInFlightDraftId = null;
  }
}

/**
 * On review screen: verify bound backendProjectId exists.
 * Stale 404 → reconcile by draft pointer → else clear binding (recoverable new draft, not terminal).
 */
export async function verifyIntakeBackendProjectBinding(
  draft: ProjectIntakeDraft,
): Promise<ProjectIntakeDraft> {
  const mode = getIntegrationMode();
  if (mode === "mock" || !canUseBackendApi()) {
    return draft;
  }

  const sync = draft.backendSync;
  const boundId = sync?.backendProjectId;
  if (!boundId) {
    return draft;
  }

  try {
    await fetchProject(boundId);
    if (sync?.lastSyncError?.includes("не найден")) {
      return persistLocal(
        withSyncMeta(draft, {
          lastSyncError: null,
        }),
      );
    }
    return draft;
  } catch (err) {
    const normalized = normalizeProjectWriteError(err);
    if (normalized.kind !== "project_not_found") {
      return draft;
    }

    const reconciled = await tryReconcileByDraftId(draft.id);
    if (reconciled) {
      return persistLocal(
        withSyncMeta(draft, {
          backendProjectId: reconciled.id,
          backendSyncState: "partially_synced",
          backendUpdatedAt: reconciled.updated_at,
          lastSyncError: null,
        }),
      );
    }

    return persistLocal(
      withSyncMeta(draft, {
        backendProjectId: null,
        backendSyncState: "local_only",
        lastSyncError: null,
      }),
    );
  }
}

export async function reconcileIntakeProject(
  draft: ProjectIntakeDraft,
): Promise<ProjectSyncResult> {
  const mode = getIntegrationMode();
  if (mode === "mock") {
    return syncIntakeProject(draft);
  }
  const found = await tryReconcileByDraftId(draft.id);
  if (!found) {
    const failed = persistLocal(
      withSyncMeta(draft, {
        backendSyncState: "conflict",
        lastSyncError: "Проект по этому черновику не найден в Workspace.",
      }),
    );
    return {
      ok: false,
      mode,
      draft: failed,
      error: {
        kind: "conflict",
        message: "Не удалось сверить проект. Повторный create не выполнен.",
        status: null,
        actionHint: "Проверьте Workspace вручную или создайте новый черновик.",
      },
      investigationMockOnly: true,
    };
  }
  const linked = persistLocal(
    withSyncMeta(draft, {
      backendProjectId: found.id,
      backendSyncState: "partially_synced",
      backendSyncedAt: new Date().toISOString(),
      backendUpdatedAt: found.updated_at,
      lastSyncError: null,
    }),
  );
  return successResult(mode, found.id, linked, "backend");
}

export function primaryCtaLabel(
  mode: IntegrationMode,
  sync: IntakeBackendSyncMeta | null | undefined,
): string {
  if (mode === "mock") return "Начать исследование (mock)";
  void sync;
  return "Запустить исследование";
}
