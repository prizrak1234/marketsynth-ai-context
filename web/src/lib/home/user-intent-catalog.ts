/**
 * Centralized customer-facing intent catalog (CWF.1a).
 * Metadata only — does NOT trigger Skill/MCP execution at runtime.
 */

import type { IntentCategory } from "@/lib/home/intent-routing";

export type IntentSupportStatus = "supported" | "partial" | "planned";

export type UserSubIntent = {
  id: string;
  titleKey: string;
  prefilledPromptRu: string;
  prefilledPromptEn: string;
  status: IntentSupportStatus;
  scenario: IntentCategory;
  futureSkillCandidates?: string[];
};

export type UserIntent = {
  id: string;
  titleKey: string;
  descriptionKey: string;
  emoji: string;
  status: IntentSupportStatus;
  /** When true, stay on /workspace and run BIV flow */
  triggersBiv?: boolean;
  prefilledPromptRu?: string;
  prefilledPromptEn?: string;
  scenario?: IntentCategory;
  subIntents?: UserSubIntent[];
  futureSkillCandidates?: string[];
};

export const USER_INTENTS: ReadonlyArray<UserIntent> = [
  {
    id: "validate-idea",
    titleKey: "intent.validateIdea.title",
    descriptionKey: "intent.validateIdea.description",
    emoji: "🔍",
    status: "supported",
    triggersBiv: true,
    prefilledPromptRu: "Хочу проверить бизнес-идею перед вложениями.",
    prefilledPromptEn: "I want to validate a business idea before investing.",
    scenario: "idea_validation",
    futureSkillCandidates: [
      "MS-SKILL-001",
      "MS-SKILL-002",
      "MS-SKILL-003",
      "MS-SKILL-004",
      "MS-SKILL-005",
    ],
  },
  {
    id: "create-content",
    titleKey: "intent.createContent.title",
    descriptionKey: "intent.createContent.description",
    emoji: "✍",
    status: "supported",
    futureSkillCandidates: [
      "MS-SKILL-012",
      "MS-SKILL-015",
      "MS-SKILL-016",
      "MS-SKILL-019",
      "MS-SKILL-020",
    ],
    subIntents: [
      {
        id: "telegram-post",
        titleKey: "intent.sub.telegramPost",
        prefilledPromptRu: "Подготовить пост для Telegram-канала.",
        prefilledPromptEn: "Prepare a post for a Telegram channel.",
        status: "supported",
        scenario: "content",
      },
      {
        id: "youtube-script",
        titleKey: "intent.sub.youtubeScript",
        prefilledPromptRu: "Подготовить сценарий для YouTube.",
        prefilledPromptEn: "Prepare a YouTube script.",
        status: "supported",
        scenario: "youtube",
      },
      {
        id: "content-plan",
        titleKey: "intent.sub.contentPlan",
        prefilledPromptRu: "Подготовить контент-план.",
        prefilledPromptEn: "Prepare a content plan.",
        status: "supported",
        scenario: "social_media",
      },
      {
        id: "social-post",
        titleKey: "intent.sub.socialPost",
        prefilledPromptRu: "Подготовить пост для социальных сетей.",
        prefilledPromptEn: "Prepare a social media post.",
        status: "partial",
        scenario: "social_media",
      },
      {
        id: "ad-copy",
        titleKey: "intent.sub.adCopy",
        prefilledPromptRu: "Подготовить рекламный текст.",
        prefilledPromptEn: "Prepare ad copy.",
        status: "partial",
        scenario: "content",
      },
    ],
  },
  {
    id: "grow-business",
    titleKey: "intent.growBusiness.title",
    descriptionKey: "intent.growBusiness.description",
    emoji: "📈",
    status: "partial",
    prefilledPromptRu:
      "Найти точки роста, улучшить позиционирование, оффер и продажи.",
    prefilledPromptEn: "Find growth levers and improve positioning, offer, and sales.",
    scenario: "marketing_strategy",
    futureSkillCandidates: [
      "MS-SKILL-003",
      "MS-SKILL-004",
      "MS-SKILL-006",
      "MS-SKILL-007",
      "MS-SKILL-010",
    ],
  },
  {
    id: "market-research",
    titleKey: "intent.marketResearch.title",
    descriptionKey: "intent.marketResearch.description",
    emoji: "📊",
    status: "partial",
    prefilledPromptRu:
      "Изучить нишу, аудиторию, конкурентов и рыночные возможности.",
    prefilledPromptEn: "Research the niche, audience, competitors, and market opportunities.",
    scenario: "market_research",
    futureSkillCandidates: ["MS-SKILL-002", "MS-SKILL-003", "MS-SKILL-004"],
  },
  {
    id: "prepare-launch",
    titleKey: "intent.prepareLaunch.title",
    descriptionKey: "intent.prepareLaunch.description",
    emoji: "🚀",
    status: "partial",
    prefilledPromptRu:
      "Собрать предложение, план запуска и материалы для выхода на рынок.",
    prefilledPromptEn: "Prepare offer, launch plan, and go-to-market materials.",
    scenario: "marketing_strategy",
    futureSkillCandidates: ["MS-SKILL-006", "MS-SKILL-007", "MS-SKILL-012"],
  },
  {
    id: "create-website",
    titleKey: "intent.createWebsite.title",
    descriptionKey: "intent.createWebsite.description",
    emoji: "🌐",
    status: "partial",
    prefilledPromptRu:
      "Подготовить структуру лендинга, оффер, тексты и рекомендации по конверсии.",
    prefilledPromptEn:
      "Prepare landing structure, offer, copy, and conversion recommendations.",
    scenario: "website",
    futureSkillCandidates: [
      "MS-SKILL-006",
      "MS-SKILL-007",
      "MS-SKILL-010",
      "MS-SKILL-011",
      "MS-SKILL-012",
    ],
  },
];

export function getIntentById(id: string): UserIntent | undefined {
  return USER_INTENTS.find((intent) => intent.id === id);
}

export function intentPrefilledPrompt(
  intent: UserIntent,
  locale: string,
): string {
  return locale === "en"
    ? intent.prefilledPromptEn || ""
    : intent.prefilledPromptRu || "";
}

export function subIntentPrefilledPrompt(
  sub: UserSubIntent,
  locale: string,
): string {
  return locale === "en" ? sub.prefilledPromptEn : sub.prefilledPromptRu;
}
