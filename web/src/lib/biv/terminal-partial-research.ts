/** Persist terminal partial BIV run ids for refresh hydration (validated against backend). */

export type TerminalPartialResearch = {
  projectId: string;
  userRequestId: string;
  runId: string;
  savedAt: number;
};

const STORAGE_KEY = "ms_terminal_partial_biv_research";

export function persistTerminalPartialResearch(session: TerminalPartialResearch): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    /* quota / private mode */
  }
}

export function loadTerminalPartialResearch(): TerminalPartialResearch | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as TerminalPartialResearch;
  } catch {
    return null;
  }
}

export function clearTerminalPartialResearch(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
