/** Deterministic intent routing for Marketsynth conversational home (v1). */

import type { AppLocale } from "@/lib/i18n/config";
import { labelTaskType, translate } from "@/lib/i18n/domain-labels";

export type IntentCategory =
  | "idea_validation"
  | "market_research"
  | "competitor_analysis"
  | "content"
  | "content_plan"
  | "social_media"
  | "youtube"
  | "telegram_bot"
  | "website"
  | "saas"
  | "automation"
  | "marketing_strategy"
  | "image_generation"
  | "general"
  | "unsupported";

export type IntentRouteKind = "project_intake" | "specialist_task" | "clarify";

export type IntentRouteResult = {
  category: IntentCategory;
  kind: IntentRouteKind;
  label: string;
  clarificationQuestion: string | null;
  nextActionLabel: string;
  nextHref: string | null;
  requiresProject: boolean;
  assistantMessage: string;
  assignedSpecialist?: string | null;
  requestId?: string;
  status?: string;
};

type Rule = {
  category: IntentCategory;
  kind: IntentRouteKind;
  requiresProject: boolean;
  patterns: RegExp[];
  actionKey: string;
  nextHref: string | null;
};

const RULES: Rule[] = [
  {
    category: "telegram_bot",
    kind: "specialist_task",
    requiresProject: false,
    patterns: [
      /telegram[\s-]?бот/i,
      /телеграм[\s-]?бот/i,
      /\bбот\b.*запис/i,
      /созда(ть|й).*бот/i,
    ],
    actionKey: "route.openTelegram",
    nextHref: "/workspace/tasks?intent=telegram_bot",
  },
  {
    category: "youtube",
    kind: "specialist_task",
    requiresProject: false,
    patterns: [/youtube/i, /ютуб/i, /сценари(й|я).*youtube/i, /сценари(й|я).*ютуб/i],
    actionKey: "route.openYoutube",
    nextHref: "/workspace/tasks?intent=youtube",
  },
  {
    category: "website",
    kind: "specialist_task",
    requiresProject: false,
    patterns: [/лендинг/i, /сайт/i, /website/i, /landing/i, /веб[\s-]?сайт/i],
    actionKey: "route.openWebsite",
    nextHref: "/workspace/tasks?intent=website",
  },
  {
    category: "saas",
    kind: "specialist_task",
    requiresProject: true,
    patterns: [/\bsaas\b/i, /саас/i, /saas[\s-]?продукт/i, /разработать saas/i],
    actionKey: "route.startIntake",
    nextHref: "/workspace/projects/new?scenario=saas",
  },
  {
    category: "social_media",
    kind: "specialist_task",
    requiresProject: false,
    patterns: [
      /контент[\s-]?план/i,
      /content[\s-]?plan/i,
      /соцсет/i,
      /telegram на месяц/i,
      /для telegram на месяц/i,
      /посты?\s+в\s+telegram/i,
    ],
    actionKey: "route.openContent",
    nextHref: "/workspace/tasks?intent=social_media",
  },
  {
    category: "image_generation",
    kind: "specialist_task",
    requiresProject: false,
    patterns: [
      /сгенерируй\s+(изображен|картинк|фото)/i,
      /созда(ть|й)\s+(изображен|картинк|иллюстрац|обложк)/i,
      /нарисуй/i,
      /визуализируй/i,
      /generate\s+(an?\s+)?(image|picture)/i,
      /create\s+(an?\s+)?(image|picture|poster)/i,
      /make\s+(an?\s+)?(image|picture|poster)/i,
    ],
    actionKey: "route.openContent",
    nextHref: "/workspace/tasks?intent=image_generation",
  },
  {
    category: "content",
    kind: "specialist_task",
    requiresProject: false,
    patterns: [/напис(ать|ать).*контент/i, /созда(ть|й).*контент/i, /post\b/i, /пост\b/i, /email/i],
    actionKey: "route.openContent",
    nextHref: "/workspace/tasks?intent=content",
  },
  {
    category: "competitor_analysis",
    kind: "project_intake",
    requiresProject: true,
    patterns: [/конкурент/i, /competitor/i],
    actionKey: "route.startIntake",
    nextHref: "/workspace/projects/new?scenario=competitor_analysis",
  },
  {
    category: "market_research",
    kind: "project_intake",
    requiresProject: true,
    patterns: [/исследова(ть|ние).*рынок/i, /market research/i, /изучить рынок/i],
    actionKey: "route.startIntake",
    nextHref: "/workspace/projects/new?scenario=market_research",
  },
  {
    category: "marketing_strategy",
    kind: "project_intake",
    requiresProject: true,
    patterns: [/маркетингов(ую|ая|ой)?\s*стратег/i, /marketing strategy/i],
    actionKey: "route.startIntake",
    nextHref: "/workspace/projects/new?scenario=marketing_strategy",
  },
  {
    category: "idea_validation",
    kind: "project_intake",
    requiresProject: true,
    patterns: [
      /бизнес[\s-]?иде/i,
      /проверить иде/i,
      /хочу открыть/i,
      /открыть.*(кофейн|стоматолог|магазин|клиник|ресторан|салон)/i,
      /валид(ация|ировать)/i,
      /idea validation/i,
    ],
    actionKey: "route.startIntake",
    nextHref: "/workspace/projects/new?scenario=idea_validation",
  },
];

function resultFromRule(
  locale: AppLocale,
  rule: Rule,
  extra?: string,
): IntentRouteResult {
  const label = labelTaskType(locale, rule.category);
  const base = translate(locale, `route.${rule.category}`);
  return {
    category: rule.category,
    kind: rule.kind,
    label,
    clarificationQuestion: null,
    nextActionLabel: translate(locale, rule.actionKey),
    nextHref: rule.nextHref,
    requiresProject: rule.requiresProject,
    assistantMessage: extra ? `${base} ${extra}` : base,
  };
}

export function isAmbiguousRequest(text: string): boolean {
  const t = text.trim().toLowerCase();
  if (!t) return true;
  if (
    /^(нужна|хочу|сделай|запусти)?\s*реклам/i.test(t) ||
    /^реклам[ауы]?\s*$/i.test(t) ||
    (/реклам/i.test(t) &&
      !/продукт|аудитор|бюджет|youtube|instagram|telegram|лендинг|сайт/i.test(t))
  ) {
    return true;
  }
  if (t.length < 12 && !RULES.some((r) => r.patterns.some((p) => p.test(t)))) {
    return true;
  }
  return false;
}

export function routeUserIntent(
  text: string,
  selectedScenario?: IntentCategory | null,
  locale: AppLocale = "ru",
): IntentRouteResult {
  const trimmed = text.trim();

  if (selectedScenario) {
    const fromScenario = routeFromCategory(locale, selectedScenario, trimmed);
    if (fromScenario) return fromScenario;
  }

  if (isAmbiguousRequest(trimmed)) {
    return {
      category: "general",
      kind: "clarify",
      label: translate(locale, "route.needsClarity"),
      clarificationQuestion: /реклам/i.test(trimmed)
        ? translate(locale, "route.clarifyAdvertising")
        : translate(locale, "route.clarifyGeneral"),
      nextActionLabel: translate(locale, "route.answerClarify"),
      nextHref: null,
      requiresProject: false,
      assistantMessage: translate(locale, "route.clarifyAmbiguous"),
    };
  }

  for (const rule of RULES) {
    if (rule.patterns.some((p) => p.test(trimmed))) {
      return resultFromRule(locale, rule);
    }
  }

  return {
    category: "general",
    kind: "clarify",
    label: translate(locale, "route.generalRequest"),
    clarificationQuestion: translate(locale, "route.clarifyFallback"),
    nextActionLabel: translate(locale, "route.refine"),
    nextHref: null,
    requiresProject: false,
    assistantMessage: translate(locale, "route.clarifyAmbiguous"),
  };
}

function routeFromCategory(
  locale: AppLocale,
  category: IntentCategory,
  text: string,
): IntentRouteResult | null {
  const rule = RULES.find((r) => r.category === category);
  if (!rule) {
    if (category === "general") {
      return routeUserIntent(text || "другое", null, locale);
    }
    return null;
  }
  const label = labelTaskType(locale, rule.category);
  const chosen = translate(locale, "route.scenarioChosen", { label });
  return resultFromRule(locale, rule, text ? chosen : undefined);
}

/** True when route must NOT open Investigation. */
export function avoidsInvestigation(category: IntentCategory): boolean {
  return (
    category === "content" ||
    category === "content_plan" ||
    category === "social_media" ||
    category === "youtube" ||
    category === "telegram_bot" ||
    category === "website" ||
    category === "automation"
  );
}
