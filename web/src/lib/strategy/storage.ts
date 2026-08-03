/**
 * Local strategy store — versioned by projectId.
 */

import type { MarketingStrategy, StrategyStore } from "@/lib/strategy/types";

const keyFor = (projectId: string) =>
  `marketsynth.product_alpha.strategy.v1.${projectId}`;

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function strategyStorageKey(projectId: string): string {
  return keyFor(projectId);
}

export function loadStrategyStore(projectId: string): StrategyStore {
  if (!canUseStorage()) {
    return emptyStore(projectId);
  }
  try {
    const raw = window.localStorage.getItem(keyFor(projectId));
    if (!raw) return emptyStore(projectId);
    const parsed = JSON.parse(raw) as StrategyStore;
    if (!parsed?.projectId || parsed.projectId !== projectId) return emptyStore(projectId);
    return parsed;
  } catch {
    return emptyStore(projectId);
  }
}

function emptyStore(projectId: string): StrategyStore {
  return {
    projectId,
    currentStrategyId: null,
    versions: [],
    updatedAt: new Date().toISOString(),
  };
}

export function saveStrategyStore(store: StrategyStore): void {
  if (!canUseStorage()) return;
  window.localStorage.setItem(
    keyFor(store.projectId),
    JSON.stringify({ ...store, updatedAt: new Date().toISOString() }),
  );
}

export function getCurrentStrategy(projectId: string): MarketingStrategy | null {
  const store = loadStrategyStore(projectId);
  if (!store.currentStrategyId) return null;
  return store.versions.find((v) => v.id === store.currentStrategyId) ?? null;
}

export function listStrategyVersions(projectId: string): MarketingStrategy[] {
  return loadStrategyStore(projectId)
    .versions.slice()
    .sort((a, b) => b.version - a.version);
}

export function nextStrategyVersion(projectId: string): number {
  const versions = loadStrategyStore(projectId).versions;
  if (versions.length === 0) return 1;
  return Math.max(...versions.map((v) => v.version)) + 1;
}

export function commitStrategyVersion(strategy: MarketingStrategy): StrategyStore {
  const store = loadStrategyStore(strategy.projectId);
  const versions = store.versions.map((v) =>
    v.id === store.currentStrategyId && v.status !== "superseded"
      ? { ...v, status: "superseded" as const }
      : v,
  );
  versions.push(strategy);
  const next: StrategyStore = {
    projectId: strategy.projectId,
    currentStrategyId: strategy.id,
    versions,
    updatedAt: new Date().toISOString(),
  };
  saveStrategyStore(next);
  return next;
}

export function updateStrategyStatus(
  projectId: string,
  strategyId: string,
  status: MarketingStrategy["status"],
): StrategyStore {
  const store = loadStrategyStore(projectId);
  const versions = store.versions.map((v) =>
    v.id === strategyId ? { ...v, status, updatedAt: new Date().toISOString() } : v,
  );
  const next = { ...store, versions, updatedAt: new Date().toISOString() };
  saveStrategyStore(next);
  return next;
}
