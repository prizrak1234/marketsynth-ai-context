/**
 * Local execution package store — versioned by projectId.
 */

import type {
  ExecutionPackage,
  ExecutionPackageStore,
} from "@/lib/execution-package/types";

const keyFor = (projectId: string) =>
  `marketsynth.product_alpha.execution_package.v1.${projectId}`;

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function executionPackageStorageKey(projectId: string): string {
  return keyFor(projectId);
}

function emptyStore(projectId: string): ExecutionPackageStore {
  return {
    projectId,
    currentPackageId: null,
    versions: [],
    updatedAt: new Date().toISOString(),
  };
}

export function loadPackageStore(projectId: string): ExecutionPackageStore {
  if (!canUseStorage()) return emptyStore(projectId);
  try {
    const raw = window.localStorage.getItem(keyFor(projectId));
    if (!raw) return emptyStore(projectId);
    const parsed = JSON.parse(raw) as ExecutionPackageStore;
    if (!parsed?.projectId || parsed.projectId !== projectId) return emptyStore(projectId);
    return parsed;
  } catch {
    return emptyStore(projectId);
  }
}

export function savePackageStore(store: ExecutionPackageStore): void {
  if (!canUseStorage()) return;
  window.localStorage.setItem(
    keyFor(store.projectId),
    JSON.stringify({ ...store, updatedAt: new Date().toISOString() }),
  );
}

export function getCurrentPackage(projectId: string): ExecutionPackage | null {
  const store = loadPackageStore(projectId);
  if (!store.currentPackageId) return null;
  return store.versions.find((v) => v.id === store.currentPackageId) ?? null;
}

export function listPackageVersions(projectId: string): ExecutionPackage[] {
  return loadPackageStore(projectId)
    .versions.slice()
    .sort((a, b) => b.version - a.version);
}

export function nextPackageVersion(projectId: string): number {
  const versions = loadPackageStore(projectId).versions;
  if (versions.length === 0) return 1;
  return Math.max(...versions.map((v) => v.version)) + 1;
}

export function commitPackageVersion(pkg: ExecutionPackage): ExecutionPackageStore {
  const store = loadPackageStore(pkg.projectId);
  const versions = store.versions.map((v) =>
    v.id === store.currentPackageId && v.status !== "superseded"
      ? { ...v, status: "superseded" as const }
      : v,
  );
  versions.push(pkg);
  const next: ExecutionPackageStore = {
    projectId: pkg.projectId,
    currentPackageId: pkg.id,
    versions,
    updatedAt: new Date().toISOString(),
  };
  savePackageStore(next);
  return next;
}

export function updatePackageStatus(
  projectId: string,
  packageId: string,
  status: ExecutionPackage["status"],
): ExecutionPackageStore {
  const store = loadPackageStore(projectId);
  const versions = store.versions.map((v) =>
    v.id === packageId
      ? { ...v, status, updatedAt: new Date().toISOString() }
      : v,
  );
  const next = { ...store, versions, updatedAt: new Date().toISOString() };
  savePackageStore(next);
  return next;
}

export function replaceCurrentPackage(pkg: ExecutionPackage): ExecutionPackageStore {
  const store = loadPackageStore(pkg.projectId);
  const versions = store.versions.map((v) => (v.id === pkg.id ? pkg : v));
  const next = {
    ...store,
    versions,
    currentPackageId: pkg.id,
    updatedAt: new Date().toISOString(),
  };
  savePackageStore(next);
  return next;
}
