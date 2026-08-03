/** Minimal UserIntentDraft model + local conversation history (home v1). */

import type {
  BackendContentDraft,
  BackendResearchCollection,
} from "@/lib/api/types/user-requests";
import type { IntentCategory, IntentRouteResult } from "@/lib/home/intent-routing";

export type IntentDraftStatus =
  | "draft"
  | "submitted"
  | "needs_clarification"
  | "routed";

export type UserIntentDraft = {
  id: string;
  text: string;
  selected_scenario: IntentCategory | null;
  created_at: string;
  status: IntentDraftStatus;
  route_result: IntentRouteResult | null;
};

export type HomeChatRole = "user" | "assistant" | "system";

export type HomeChatMessage = {
  id: string;
  role: HomeChatRole;
  text: string;
  created_at: string;
  clientMessageId?: string;
  requestId?: string;
  route?: IntentRouteResult | null;
  skillCode?: string | null;
  generatedVisualAssetIds?: string[];
  generationStatus?: string | null;
  generationWarnings?: string[];
  contentDraft?: BackendContentDraft | null;
  contentDraftReviewStatus?: string | null;
  assignedSpecialist?: string | null;
  promptPackageHash?: string | null;
  executionProvider?: string | null;
  executionModel?: string | null;
  researchCollection?: BackendResearchCollection | null;
};

const STORAGE_KEY = "marketsynth.home.conversation.v1";

export type HomeConversationState = {
  draftText: string;
  messages: HomeChatMessage[];
  lastDraft: UserIntentDraft | null;
};

function emptyState(): HomeConversationState {
  return { draftText: "", messages: [], lastDraft: null };
}

export function loadHomeConversation(): HomeConversationState {
  if (typeof window === "undefined") return emptyState();
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyState();
    const parsed = JSON.parse(raw) as HomeConversationState;
    if (!parsed || !Array.isArray(parsed.messages)) return emptyState();
    return {
      draftText: typeof parsed.draftText === "string" ? parsed.draftText : "",
      messages: parsed.messages,
      lastDraft: parsed.lastDraft ?? null,
    };
  } catch {
    return emptyState();
  }
}

export function saveHomeConversation(state: HomeConversationState): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* ignore quota */
  }
}

export function newId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}_${Date.now().toString(36)}`;
}

export function createDraft(
  text: string,
  selected: IntentCategory | null,
  status: IntentDraftStatus,
  route: IntentRouteResult | null,
): UserIntentDraft {
  return {
    id: newId("intent"),
    text,
    selected_scenario: selected,
    created_at: new Date().toISOString(),
    status,
    route_result: route,
  };
}
