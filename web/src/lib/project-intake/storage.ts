/**
 * LocalStorage adapter for Product Alpha intake drafts and mock projects.
 * Isolated — no backend API.
 */

import { createEmptyDraft } from "@/lib/project-intake/schema";
import type {
  MockInvestigationProject,
  ProjectIntakeDraft,
} from "@/lib/project-intake/types";

const DRAFT_KEY = "marketsynth.product_alpha.intake_draft.v1";
const PROJECTS_KEY = "marketsynth.product_alpha.mock_projects.v1";
const LINKED_DRAFT_PREFIX = "marketsynth.product_alpha.intake_draft.by_project.v1.";

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function linkedIntakeDraftKey(projectId: string): string {
  return `${LINKED_DRAFT_PREFIX}${projectId}`;
}

export function loadIntakeDraft(): ProjectIntakeDraft {
  if (!canUseStorage()) return createEmptyDraft();
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY);
    if (!raw) return createEmptyDraft();
    const parsed = JSON.parse(raw) as ProjectIntakeDraft;
    if (!parsed?.id || !parsed.projectBasics) return createEmptyDraft();
    return parsed;
  } catch {
    return createEmptyDraft();
  }
}

export function saveIntakeDraft(draft: ProjectIntakeDraft): void {
  if (!canUseStorage()) return;
  const next = { ...draft, updatedAt: draft.updatedAt || new Date().toISOString() };
  window.localStorage.setItem(DRAFT_KEY, JSON.stringify(next));
}

/** Preserve full intake against backend project id (I2). */
export function saveLinkedIntakeDraft(projectId: string, draft: ProjectIntakeDraft): void {
  if (!canUseStorage() || !projectId) return;
  window.localStorage.setItem(linkedIntakeDraftKey(projectId), JSON.stringify(draft));
}

export function loadLinkedIntakeDraft(projectId: string): ProjectIntakeDraft | null {
  if (!canUseStorage() || !projectId) return null;
  try {
    const raw = window.localStorage.getItem(linkedIntakeDraftKey(projectId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ProjectIntakeDraft;
    if (!parsed?.id || !parsed.projectBasics) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearIntakeDraft(): void {
  if (!canUseStorage()) return;
  window.localStorage.removeItem(DRAFT_KEY);
}

export function loadMockProjects(): MockInvestigationProject[] {
  if (!canUseStorage()) return [];
  try {
    const raw = window.localStorage.getItem(PROJECTS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as MockInvestigationProject[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveMockProject(project: MockInvestigationProject): void {
  if (!canUseStorage()) return;
  const all = loadMockProjects().filter((p) => p.id !== project.id);
  all.unshift(project);
  window.localStorage.setItem(PROJECTS_KEY, JSON.stringify(all.slice(0, 20)));
}

export function getMockProject(id: string): MockInvestigationProject | null {
  return loadMockProjects().find((p) => p.id === id) ?? null;
}
