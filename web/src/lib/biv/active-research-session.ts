/** Persist in-flight BIV research across refresh/remount (sessionStorage). */

export type ActiveResearchSession = {
  projectId: string;
  userRequestId: string;
  contextId: string;
  inputSnapshotHash: string;
  runId?: string | null;
  startedAt: number;
};

const STORAGE_KEY = "ms_active_biv_research";

export function persistActiveResearchSession(session: ActiveResearchSession): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    /* quota / private mode */
  }
}

export function loadActiveResearchSession(): ActiveResearchSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as ActiveResearchSession;
  } catch {
    return null;
  }
}

export function clearActiveResearchSession(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
