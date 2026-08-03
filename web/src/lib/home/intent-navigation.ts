/** Navigation helpers for customer intents (CWF.1a). */

import type { AppLocale } from "@/lib/i18n/config";
import {
  intentPrefilledPrompt,
  subIntentPrefilledPrompt,
  type UserIntent,
  type UserSubIntent,
} from "@/lib/home/user-intent-catalog";
import { routeUserIntent, type IntentCategory } from "@/lib/home/intent-routing";

const TASK_STORAGE_KEY = "marketsynth.intent.task.v1";

export type IntentNavigationTarget =
  | { kind: "biv"; task: string; scenario: IntentCategory }
  | { kind: "canonical_intake"; task: string; scenario: IntentCategory }
  | { kind: "assistant"; task: string; scenario: IntentCategory | null; partial?: boolean };

export function saveIntentTask(task: string, scenario?: string | null): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(
      TASK_STORAGE_KEY,
      JSON.stringify({ task, scenario: scenario ?? null, savedAt: Date.now() }),
    );
  } catch {
    /* ignore */
  }
}

export function loadIntentTask(): { task: string; scenario: string | null } | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(TASK_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { task?: string; scenario?: string | null };
    if (!parsed?.task) return null;
    return { task: parsed.task, scenario: parsed.scenario ?? null };
  } catch {
    return null;
  }
}

export function buildAssistantHref(task: string, scenario?: IntentCategory | null): string {
  const params = new URLSearchParams();
  if (task.trim()) params.set("task", task.trim());
  if (scenario) params.set("scenario", scenario);
  const qs = params.toString();
  return qs ? `/workspace/assistant?${qs}` : "/workspace/assistant";
}

export function resolveIntentSelection(
  intent: UserIntent,
  locale: AppLocale,
  subIntent?: UserSubIntent,
): IntentNavigationTarget {
  if (intent.triggersBiv) {
    const task = subIntent
      ? subIntentPrefilledPrompt(subIntent, locale)
      : intentPrefilledPrompt(intent, locale);
    return { kind: "biv", task, scenario: "idea_validation" };
  }

  if (subIntent) {
    return {
      kind: "assistant",
      task: subIntentPrefilledPrompt(subIntent, locale),
      scenario: subIntent.scenario,
      partial: subIntent.status === "partial",
    };
  }

  const task = intentPrefilledPrompt(intent, locale);
  return {
    kind: "assistant",
    task,
    scenario: intent.scenario ?? null,
    partial: intent.status === "partial",
  };
}

export function resolveFreeTextTask(text: string, locale: AppLocale): IntentNavigationTarget {
  const trimmed = text.trim();
  const route = routeUserIntent(trimmed, null, locale);

  if (route.category === "idea_validation") {
    return { kind: "biv", task: trimmed, scenario: "idea_validation" };
  }

  const scenario =
    route.category && route.category !== "general" && route.category !== "unsupported"
      ? route.category
      : null;

  return {
    kind: "assistant",
    task: trimmed,
    scenario,
    partial: route.kind === "clarify",
  };
}

export function navigateToAssistant(
  router: { push: (href: string) => void },
  task: string,
  scenario?: IntentCategory | null,
): void {
  saveIntentTask(task, scenario);
  router.push(buildAssistantHref(task, scenario));
}
