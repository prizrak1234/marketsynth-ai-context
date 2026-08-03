import type { IntentCategory } from "@/lib/home/intent-routing";

export type HomeScenario = {
  id: IntentCategory | "other";
  /** Optional seed text placed into the input / submitted. */
  seedKey?: string;
  seedTextRu: string;
  seedTextEn: string;
  category: IntentCategory | null;
  /** Translation key for card label; falls back to task.type.{id}. */
  labelKey: string;
};

export const HOME_SCENARIOS: ReadonlyArray<HomeScenario> = [
  {
    id: "idea_validation",
    labelKey: "task.type.idea_validation",
    seedTextRu: "Хочу проверить бизнес-идею перед вложениями.",
    seedTextEn: "I want to validate a business idea before investing.",
    category: "idea_validation",
  },
  {
    id: "market_research",
    labelKey: "task.type.market_research",
    seedTextRu: "Нужно исследовать рынок и понять спрос.",
    seedTextEn: "I need market research and demand insight.",
    category: "market_research",
  },
  {
    id: "competitor_analysis",
    labelKey: "task.type.competitor_analysis",
    seedTextRu: "Проанализируй конкурентов в моей нише.",
    seedTextEn: "Analyze competitors in my niche.",
    category: "competitor_analysis",
  },
  {
    id: "marketing_strategy",
    labelKey: "task.type.marketing_strategy",
    seedTextRu: "Нужна маркетинговая стратегия для запуска.",
    seedTextEn: "I need a marketing strategy for launch.",
    category: "marketing_strategy",
  },
  {
    id: "content",
    labelKey: "task.type.content",
    seedTextRu: "Напиши контент для публикации.",
    seedTextEn: "Write content for publication.",
    category: "content",
  },
  {
    id: "content_plan",
    labelKey: "task.type.content_plan",
    seedTextRu: "Сделай контент-план для Telegram на месяц.",
    seedTextEn: "Create a one-month Telegram content plan.",
    category: "content_plan",
  },
  {
    id: "social_media",
    labelKey: "task.type.social_media",
    seedTextRu: "Нужен контент для социальных сетей.",
    seedTextEn: "I need social media content.",
    category: "social_media",
  },
  {
    id: "youtube",
    labelKey: "task.type.youtube",
    seedTextRu: "Подготовь сценарий для YouTube.",
    seedTextEn: "Prepare a YouTube script.",
    category: "youtube",
  },
  {
    id: "telegram_bot",
    labelKey: "task.type.telegram_bot",
    seedTextRu: "Создай Telegram-бота для записи клиентов.",
    seedTextEn: "Create a Telegram bot for client bookings.",
    category: "telegram_bot",
  },
  {
    id: "website",
    labelKey: "task.type.website",
    seedTextRu: "Нужен лендинг для продукта.",
    seedTextEn: "I need a landing page for the product.",
    category: "website",
  },
  {
    id: "saas",
    labelKey: "task.type.saas",
    seedTextRu: "Хочу разработать SaaS-продукт.",
    seedTextEn: "I want to build a SaaS product.",
    category: "saas",
  },
  {
    id: "automation",
    labelKey: "task.type.automation",
    seedTextRu: "Автоматизируй обработку заявок с сайта.",
    seedTextEn: "Automate lead intake from the website.",
    category: "automation",
  },
  {
    id: "other",
    labelKey: "home.scenarioOther",
    seedTextRu: "",
    seedTextEn: "",
    category: null,
  },
];

export function scenarioSeed(scenario: HomeScenario, locale: string): string {
  return locale === "en" ? scenario.seedTextEn : scenario.seedTextRu;
}
