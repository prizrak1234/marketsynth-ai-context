/**
 * Node-runnable readiness self-check (no test runner in web package).
 * Run: npx --yes tsx src/lib/project-intake/readiness.selfcheck.ts
 * from web/
 */

import { createEmptyDraft } from "./schema";
import { canStartInvestigation, evaluateIntakeReadiness } from "./readiness";
import type { ProjectIntakeDraft } from "./types";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

function fillMinimal(draft: ProjectIntakeDraft): ProjectIntakeDraft {
  return {
    ...draft,
    projectBasics: {
      name: "Clinic leads",
      ideaDescription: "Проверить спрос на лидогенерацию для стоматологий в Москве",
      businessType: "local_business",
      projectStage: "validating_demand",
      geography: "Москва",
      interfaceLanguage: "ru",
    },
    product: {
      ...draft.product,
      whatIsSold: "Пакет лидов в клинику",
      primaryProblem: "Пустующее расписание",
      valueProposition: "Квалифицированные заявки без своей рекламы",
      priceUnknown: true,
      deliveryUnknown: false,
      deliveryModel: "онлайн + call-center",
    },
    market: {
      ...draft.market,
      targetMarket: "Частные стоматологии 1–5 кресел",
      geography: "Москва",
      competitorsUnknown: true,
      demandUnavailable: true,
      marketSizeUnknown: true,
    },
    audience: {
      ...draft.audience,
      customerModel: "b2b",
      segments: [
        {
          id: "s1",
          label: "Владельцы клиник",
          notes: "Ищут стабильный поток пациентов",
        },
      ],
    },
    economics: {
      ...draft.economics,
      launchBudget: { mode: "unknown" },
      monthlyMarketingBudget: { mode: "range", min: "100000", max: "250000" },
      targetRevenue: { mode: "unknown" },
      averageOrderValue: { mode: "unknown" },
    },
  };
}

const empty = evaluateIntakeReadiness(createEmptyDraft());
assert(empty.status === "insufficient_data", "empty draft must be insufficient_data");
assert(!canStartInvestigation(empty), "empty cannot start");

const readyish = evaluateIntakeReadiness(fillMinimal(createEmptyDraft()));
assert(
  readyish.status === "ready" || readyish.status === "conditionally_ready",
  `filled draft expected ready/conditional, got ${readyish.status}`,
);
assert(canStartInvestigation(readyish), "filled draft must allow start");

const vague = fillMinimal(createEmptyDraft());
vague.projectBasics.ideaDescription = "идея";
const vagueResult = evaluateIntakeReadiness(vague);
assert(
  vagueResult.status === "insufficient_data",
  "vague idea must be insufficient_data",
);

console.log("readiness.selfcheck: OK");
