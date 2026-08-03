/**
 * Local implementation plan store — versioned by projectId.
 */

import type {
  ImplementationPlan,
  ImplementationPlanStore,
} from "@/lib/implementation-plan/types";

const keyFor = (projectId: string) =>
  `marketsynth.product_alpha.implementation_plan.v1.${projectId}`;

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function implementationPlanStorageKey(projectId: string): string {
  return keyFor(projectId);
}

function emptyStore(projectId: string): ImplementationPlanStore {
  return {
    projectId,
    currentPlanId: null,
    versions: [],
    updatedAt: new Date().toISOString(),
  };
}

export function loadPlanStore(projectId: string): ImplementationPlanStore {
  if (!canUseStorage()) return emptyStore(projectId);
  try {
    const raw = window.localStorage.getItem(keyFor(projectId));
    if (!raw) return emptyStore(projectId);
    const parsed = JSON.parse(raw) as ImplementationPlanStore;
    if (!parsed?.projectId || parsed.projectId !== projectId) return emptyStore(projectId);
    return parsed;
  } catch {
    return emptyStore(projectId);
  }
}

export function savePlanStore(store: ImplementationPlanStore): void {
  if (!canUseStorage()) return;
  window.localStorage.setItem(
    keyFor(store.projectId),
    JSON.stringify({ ...store, updatedAt: new Date().toISOString() }),
  );
}

export function getCurrentPlan(projectId: string): ImplementationPlan | null {
  const store = loadPlanStore(projectId);
  if (!store.currentPlanId) return null;
  return store.versions.find((v) => v.id === store.currentPlanId) ?? null;
}

export function listPlanVersions(projectId: string): ImplementationPlan[] {
  return loadPlanStore(projectId)
    .versions.slice()
    .sort((a, b) => b.version - a.version);
}

export function nextPlanVersion(projectId: string): number {
  const versions = loadPlanStore(projectId).versions;
  if (versions.length === 0) return 1;
  return Math.max(...versions.map((v) => v.version)) + 1;
}

export function commitPlanVersion(plan: ImplementationPlan): ImplementationPlanStore {
  const store = loadPlanStore(plan.projectId);
  const versions = store.versions.map((v) =>
    v.id === store.currentPlanId && v.status !== "superseded"
      ? { ...v, status: "superseded" as const }
      : v,
  );
  versions.push(plan);
  const next: ImplementationPlanStore = {
    projectId: plan.projectId,
    currentPlanId: plan.id,
    versions,
    updatedAt: new Date().toISOString(),
  };
  savePlanStore(next);
  return next;
}

export function updatePlanStatus(
  projectId: string,
  planId: string,
  status: ImplementationPlan["status"],
): ImplementationPlanStore {
  const store = loadPlanStore(projectId);
  const versions = store.versions.map((v) =>
    v.id === planId ? { ...v, status, updatedAt: new Date().toISOString() } : v,
  );
  const next = { ...store, versions, updatedAt: new Date().toISOString() };
  savePlanStore(next);
  return next;
}
