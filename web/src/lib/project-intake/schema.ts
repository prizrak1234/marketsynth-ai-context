/**
 * Empty draft factory + option labels for Product Alpha intake.
 */

import type {
  AudienceSegment,
  EconomicsDraft,
  IntakeStepId,
  MarketDraft,
  MaterialsDraft,
  MoneyValue,
  ProductDraft,
  ProjectBasics,
  ProjectIntakeDraft,
} from "@/lib/project-intake/types";

export const INTAKE_STEPS: ReadonlyArray<{
  id: IntakeStepId;
  path: string;
  label: string;
  shortLabel: string;
}> = [
  {
    id: "basics",
    path: "/workspace/projects/new",
    label: "О проекте",
    shortLabel: "1. Basics",
  },
  {
    id: "product",
    path: "/workspace/projects/new/idea",
    label: "Продукт / услуга",
    shortLabel: "2. Product",
  },
  {
    id: "market",
    path: "/workspace/projects/new/market",
    label: "Рынок и конкуренты",
    shortLabel: "3. Market",
  },
  {
    id: "audience",
    path: "/workspace/projects/new/audience",
    label: "Аудитория",
    shortLabel: "4. Audience",
  },
  {
    id: "economics",
    path: "/workspace/projects/new/economics",
    label: "Экономика",
    shortLabel: "5. Economics",
  },
  {
    id: "materials",
    path: "/workspace/projects/new/materials",
    label: "Материалы",
    shortLabel: "6. Materials",
  },
  {
    id: "review",
    path: "/workspace/projects/new/review",
    label: "Обзор и готовность",
    shortLabel: "7. Review",
  },
];

export const BUSINESS_TYPE_OPTIONS = [
  { value: "local_business", label: "Локальный бизнес" },
  { value: "online_service", label: "Онлайн-сервис" },
  { value: "saas", label: "SaaS" },
  { value: "ecommerce", label: "E-commerce" },
  { value: "marketplace", label: "Маркетплейс" },
  { value: "franchise", label: "Франшиза" },
  { value: "professional_services", label: "Профессиональные услуги" },
  { value: "mobile_application", label: "Мобильное приложение" },
  { value: "media_content", label: "Медиа / контент" },
  { value: "other", label: "Другое" },
] as const;

export const PROJECT_STAGE_OPTIONS = [
  { value: "idea_only", label: "Только идея" },
  { value: "validating_demand", label: "Проверка спроса" },
  { value: "preparing_launch", label: "Подготовка к запуску" },
  { value: "already_operating", label: "Уже работает" },
  { value: "scaling", label: "Масштабирование" },
  { value: "relaunching", label: "Перезапуск" },
] as const;

export const CUSTOMER_MODEL_OPTIONS = [
  { value: "b2c", label: "B2C — частные клиенты" },
  { value: "b2b", label: "B2B — бизнес-клиенты" },
  { value: "b2g", label: "B2G — государство" },
  { value: "mixed", label: "Смешанная модель" },
  { value: "unknown", label: "Пока не определено" },
] as const;

export function emptyMoney(mode: MoneyValue["mode"] = "unknown"): MoneyValue {
  return { mode, exact: "", min: "", max: "" };
}

export function emptyBasics(): ProjectBasics {
  return {
    name: "",
    ideaDescription: "",
    businessType: "",
    projectStage: "",
    geography: "",
    interfaceLanguage: "ru",
  };
}

export function emptyProduct(): ProductDraft {
  return {
    whatIsSold: "",
    primaryProblem: "",
    valueProposition: "",
    price: emptyMoney("unknown"),
    deliveryModel: "",
    differentiators: "",
    knownLimitations: "",
    priceUnknown: true,
    deliveryUnknown: false,
  };
}

export function emptyMarket(): MarketDraft {
  return {
    targetMarket: "",
    geography: "",
    knownCompetitors: "",
    competitorUrls: "",
    marketAssumptions: "",
    demandEvidence: "",
    seasonality: "",
    restrictions: "",
    competitorsUnknown: false,
    demandUnavailable: false,
    marketSizeUnknown: false,
  };
}

export function newSegment(label = ""): AudienceSegment {
  return {
    id: `seg_${Math.random().toString(36).slice(2, 9)}`,
    label,
    notes: "",
  };
}

export function emptyAudience() {
  return {
    customerModel: "unknown" as const,
    segments: [newSegment()],
    decisionMaker: "",
    buyerUserDistinction: "",
    customerLocation: "",
    expectedPains: "",
    expectedObjections: "",
    currentResearch: "",
  };
}

export function emptyEconomics(): EconomicsDraft {
  return {
    launchBudget: emptyMoney("unknown"),
    monthlyMarketingBudget: emptyMoney("unknown"),
    targetRevenue: emptyMoney("unknown"),
    paybackPeriod: "",
    paybackUnknown: true,
    averageOrderValue: emptyMoney("unknown"),
    grossMargin: "",
    grossMarginUnknown: true,
    teamSize: "",
    teamSizeUnknown: true,
    internalResources: "",
    launchDeadline: "",
    launchDeadlineUnknown: true,
    criticalConstraints: "",
  };
}

export function emptyMaterials(): MaterialsDraft {
  return {
    websiteUrl: "",
    socialProfiles: "",
    items: [],
  };
}

export function createEmptyDraft(step: IntakeStepId = "basics"): ProjectIntakeDraft {
  const now = new Date().toISOString();
  return {
    id: `draft_${Math.random().toString(36).slice(2, 10)}`,
    projectBasics: emptyBasics(),
    product: emptyProduct(),
    market: emptyMarket(),
    audience: emptyAudience(),
    economics: emptyEconomics(),
    materials: emptyMaterials(),
    assumptions: [],
    missingData: [],
    readiness: null,
    currentStep: step,
    updatedAt: now,
    backendSync: {
      backendProjectId: null,
      backendSyncState: "local_only",
      backendSyncedAt: null,
      backendUpdatedAt: null,
      lastSyncError: null,
      submissionFingerprint: null,
      localDraftVersion: now,
    },
  };
}

export function stepIdFromPath(pathname: string): IntakeStepId {
  const found = INTAKE_STEPS.find((s) => s.path === pathname);
  return found?.id ?? "basics";
}

export function pathForStep(id: IntakeStepId): string {
  return INTAKE_STEPS.find((s) => s.id === id)?.path ?? "/workspace/projects/new";
}

export function nextStepId(current: IntakeStepId): IntakeStepId | null {
  const i = INTAKE_STEPS.findIndex((s) => s.id === current);
  if (i < 0 || i >= INTAKE_STEPS.length - 1) return null;
  return INTAKE_STEPS[i + 1]!.id;
}

export function prevStepId(current: IntakeStepId): IntakeStepId | null {
  const i = INTAKE_STEPS.findIndex((s) => s.id === current);
  if (i <= 0) return null;
  return INTAKE_STEPS[i - 1]!.id;
}
