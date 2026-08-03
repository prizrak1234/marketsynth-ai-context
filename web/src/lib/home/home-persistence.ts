/**
 * Durable-enough local store for Home conversation + WorkspaceTask projection.
 *
 * Backend UserRequest domain does not exist yet — localStorage is labelled
 * authority=local_draft, never presented as server SoT.
 */

import type { IntentCategory, IntentRouteResult } from "@/lib/home/intent-routing";
import type { WorkspaceTaskItem } from "@/lib/home/workspace-task-types";
import {
  createDraft,
  newId,
  type HomeChatMessage,
  type HomeConversationState,
  type UserIntentDraft,
} from "@/lib/home/user-intent-draft";

const CONV_KEY = "marketsynth.home.conversation.v1";
const TASKS_KEY = "marketsynth.workspace.tasks.v1";

function emptyConv(): HomeConversationState {
  return { draftText: "", messages: [], lastDraft: null };
}

export function loadHomeConversation(): HomeConversationState {
  if (typeof window === "undefined") return emptyConv();
  try {
    const raw =
      window.localStorage.getItem(CONV_KEY) ||
      window.sessionStorage.getItem(CONV_KEY);
    if (!raw) return emptyConv();
    const parsed = JSON.parse(raw) as HomeConversationState;
    if (!parsed || !Array.isArray(parsed.messages)) return emptyConv();
    return {
      draftText: typeof parsed.draftText === "string" ? parsed.draftText : "",
      messages: parsed.messages,
      lastDraft: parsed.lastDraft ?? null,
    };
  } catch {
    return emptyConv();
  }
}

export function saveHomeConversation(state: HomeConversationState): void {
  if (typeof window === "undefined") return;
  try {
    const payload = JSON.stringify(state);
    window.localStorage.setItem(CONV_KEY, payload);
    // Mirror for backwards compatibility with session-only readers
    window.sessionStorage.setItem(CONV_KEY, payload);
  } catch {
    /* ignore */
  }
}

export function loadLocalWorkspaceTasks(): WorkspaceTaskItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(TASKS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as WorkspaceTaskItem[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveLocalWorkspaceTasks(items: WorkspaceTaskItem[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(TASKS_KEY, JSON.stringify(items.slice(0, 200)));
  } catch {
    /* ignore */
  }
}

export function upsertLocalTaskFromRoute(input: {
  text: string;
  category: IntentCategory | null;
  route: IntentRouteResult;
  draft: UserIntentDraft;
}): WorkspaceTaskItem {
  const now = new Date().toISOString();
  const item: WorkspaceTaskItem = {
    id: input.draft.id,
    title: input.route.label || input.text.slice(0, 80) || "Задача",
    request_text: input.text,
    task_kind: input.route.kind === "clarify" ? "user_request" : "user_request",
    route_category: input.route.category,
    origin: "home_conversation",
    project_id: null,
    specialist_role: input.route.assignedSpecialist ?? null,
    status:
      input.route.kind === "clarify" ? "needs_clarification" : "routed",
    next_action: input.route.nextActionLabel,
    result_summary: null,
    created_at: input.draft.created_at || now,
    updated_at: now,
    source_domain: "home_user_intent_draft",
    source_id: input.draft.id,
    authority: "local_draft",
    next_href: input.route.nextHref,
  };
  const existing = loadLocalWorkspaceTasks().filter((t) => t.id !== item.id);
  saveLocalWorkspaceTasks([item, ...existing]);
  return item;
}

export { createDraft, newId };
export type { HomeChatMessage, HomeConversationState, UserIntentDraft };
