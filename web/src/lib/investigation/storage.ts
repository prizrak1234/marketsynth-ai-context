/**
 * Local investigation state — keyed by mock project ID.
 * Does not overwrite intake drafts.
 */

import type { InvestigationWorkspace } from "@/lib/investigation/types";

const keyFor = (projectId: string) =>
  `marketsynth.product_alpha.investigation.v1.${projectId}`;

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function loadInvestigationWorkspace(
  projectId: string,
): InvestigationWorkspace | null {
  if (!canUseStorage()) return null;
  try {
    const raw = window.localStorage.getItem(keyFor(projectId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as InvestigationWorkspace;
    if (!parsed?.projectId || parsed.projectId !== projectId) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveInvestigationWorkspace(
  workspace: InvestigationWorkspace,
): void {
  if (!canUseStorage()) return;
  const next = { ...workspace, updatedAt: new Date().toISOString() };
  window.localStorage.setItem(keyFor(workspace.projectId), JSON.stringify(next));
}

export function clearInvestigationWorkspace(projectId: string): void {
  if (!canUseStorage()) return;
  window.localStorage.removeItem(keyFor(projectId));
}

/** Test helper — storage key format */
export function investigationStorageKey(projectId: string): string {
  return keyFor(projectId);
}
