/** Hint for completed-report hydration — always validated against backend before use. */

export type LastCompletedResearch = {
  projectId: string;
  userRequestId: string;
  runId: string | null;
  completedAt: number;
};

const STORAGE_KEY = "ms_last_completed_biv_research";

export function persistLastCompletedResearch(session: LastCompletedResearch): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    /* quota / private mode */
  }
}

export function loadLastCompletedResearch(): LastCompletedResearch | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as LastCompletedResearch;
  } catch {
    return null;
  }
}

export function clearLastCompletedResearch(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
