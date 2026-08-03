/**
 * Local verdict store — versioned, scoped by projectId.
 */

import type { BusinessVerdict, VerdictStore } from "@/lib/verdict/types";

const keyFor = (projectId: string) =>
  `marketsynth.product_alpha.verdict.v1.${projectId}`;

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function verdictStorageKey(projectId: string): string {
  return keyFor(projectId);
}

export function loadVerdictStore(projectId: string): VerdictStore {
  if (!canUseStorage()) {
    return { projectId, currentVerdictId: null, versions: [], updatedAt: new Date().toISOString() };
  }
  try {
    const raw = window.localStorage.getItem(keyFor(projectId));
    if (!raw) {
      return { projectId, currentVerdictId: null, versions: [], updatedAt: new Date().toISOString() };
    }
    const parsed = JSON.parse(raw) as VerdictStore;
    if (!parsed?.projectId || parsed.projectId !== projectId) {
      return { projectId, currentVerdictId: null, versions: [], updatedAt: new Date().toISOString() };
    }
    return parsed;
  } catch {
    return { projectId, currentVerdictId: null, versions: [], updatedAt: new Date().toISOString() };
  }
}

export function saveVerdictStore(store: VerdictStore): void {
  if (!canUseStorage()) return;
  const next = { ...store, updatedAt: new Date().toISOString() };
  window.localStorage.setItem(keyFor(store.projectId), JSON.stringify(next));
}

export function getCurrentVerdict(projectId: string): BusinessVerdict | null {
  const store = loadVerdictStore(projectId);
  if (!store.currentVerdictId) return null;
  return store.versions.find((v) => v.id === store.currentVerdictId) ?? null;
}

export function listVerdictVersions(projectId: string): BusinessVerdict[] {
  return loadVerdictStore(projectId).versions.slice().sort((a, b) => b.version - a.version);
}

/** Append a new version; mark previous current as superseded. */
export function commitVerdictVersion(verdict: BusinessVerdict): VerdictStore {
  const store = loadVerdictStore(verdict.projectId);
  const versions = store.versions.map((v) =>
    v.id === store.currentVerdictId && v.status !== "superseded"
      ? { ...v, status: "superseded" as const }
      : v,
  );
  versions.push(verdict);
  const next: VerdictStore = {
    projectId: verdict.projectId,
    currentVerdictId: verdict.id,
    versions,
    updatedAt: new Date().toISOString(),
  };
  saveVerdictStore(next);
  return next;
}

export function updateVerdictStatus(
  projectId: string,
  verdictId: string,
  status: BusinessVerdict["status"],
): VerdictStore {
  const store = loadVerdictStore(projectId);
  const versions = store.versions.map((v) =>
    v.id === verdictId ? { ...v, status } : v,
  );
  const next = { ...store, versions, updatedAt: new Date().toISOString() };
  saveVerdictStore(next);
  return next;
}

export function nextVersionNumber(projectId: string): number {
  const versions = loadVerdictStore(projectId).versions;
  if (versions.length === 0) return 1;
  return Math.max(...versions.map((v) => v.version)) + 1;
}
