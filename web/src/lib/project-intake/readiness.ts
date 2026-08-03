/**
 * Deterministic local readiness — not a business viability verdict.
 */

import type {
  IntakeReadinessResult,
  MoneyValue,
  ProjectIntakeDraft,
} from "@/lib/project-intake/types";

function filled(value: string | undefined | null): boolean {
  return Boolean(value && value.trim().length > 0);
}

function moneyOk(m: MoneyValue, unknownFlag?: boolean): boolean {
  if (unknownFlag || m.mode === "unknown") return true;
  if (m.mode === "exact") return filled(m.exact);
  if (m.mode === "range") return filled(m.min) || filled(m.max);
  return false;
}

function moneyDescribed(m: MoneyValue, unknownFlag?: boolean): boolean {
  return moneyOk(m, unknownFlag);
}

export function evaluateIntakeReadiness(draft: ProjectIntakeDraft): IntakeReadinessResult {
  const completedSections: string[] = [];
  const missingCritical: string[] = [];
  const missingOptional: string[] = [];
  const assumptions: string[] = [];
  const contradictions: string[] = [];
  const recommendedAdditions: string[] = [];

  const b = draft.projectBasics;
  const basicsOk =
    filled(b.name) &&
    filled(b.ideaDescription) &&
    Boolean(b.businessType) &&
    Boolean(b.projectStage) &&
    filled(b.geography);

  if (basicsOk) completedSections.push("idea");
  else {
    if (!filled(b.name)) missingCritical.push("Название проекта");
    if (!filled(b.ideaDescription)) missingCritical.push("Краткое описание идеи");
    if (!b.businessType) missingCritical.push("Тип бизнеса");
    if (!b.projectStage) missingCritical.push("Стадия проекта");
    if (!filled(b.geography)) missingCritical.push("География");
  }

  const p = draft.product;
  const productCore =
    filled(p.whatIsSold) && filled(p.primaryProblem) && filled(p.valueProposition);
  if (productCore) completedSections.push("product");
  else {
    if (!filled(p.whatIsSold)) missingCritical.push("Что продаётся");
    if (!filled(p.primaryProblem)) missingCritical.push("Проблема клиента");
    if (!filled(p.valueProposition)) missingCritical.push("Ценностное предложение");
  }
  if (!filled(p.deliveryModel) && !p.deliveryUnknown) {
    missingOptional.push("Модель доставки");
  }
  if (p.priceUnknown || p.price.mode === "unknown") {
    assumptions.push("Цена пока неизвестна — исследование стартует без unit-price.");
  } else if (!moneyDescribed(p.price)) {
    missingOptional.push("Цена / диапазон цены");
  }

  const m = draft.market;
  const marketGeo = filled(m.geography) || filled(b.geography);
  const marketCore = filled(m.targetMarket) && marketGeo;
  if (marketCore) completedSections.push("market");
  else {
    if (!filled(m.targetMarket)) missingCritical.push("Целевой рынок");
    if (!marketGeo) missingCritical.push("География рынка");
  }
  if (m.competitorsUnknown) {
    assumptions.push("Конкуренты неизвестны — агентство проверит landscape самостоятельно.");
  } else if (!filled(m.knownCompetitors) && !filled(m.competitorUrls)) {
    missingOptional.push("Известные конкуренты или URL");
  }
  if (m.demandUnavailable) {
    assumptions.push("Данных о спросе нет — research подтвердит или опровергнет гипотезы.");
  }
  if (m.marketSizeUnknown) {
    assumptions.push("Размер рынка неизвестен владельцу.");
  }
  if (filled(m.marketAssumptions)) {
    assumptions.push(`Гипотеза рынка: ${m.marketAssumptions.trim().slice(0, 120)}`);
  }

  const a = draft.audience;
  const segments = a.segments.filter((s) => filled(s.label) || filled(s.notes));
  const audienceOk = segments.length > 0;
  if (audienceOk) completedSections.push("audience");
  else missingCritical.push("Хотя бы одна гипотеза аудитории");

  if (a.customerModel === "unknown") {
    assumptions.push("Модель клиентов (B2B/B2C/B2G) пока не зафиксирована.");
  }
  if (!filled(a.expectedPains)) missingOptional.push("Ожидаемые боли аудитории");
  if (!filled(a.decisionMaker)) missingOptional.push("ЛПР / decision maker");

  const e = draft.economics;
  const budgetsOk =
    moneyDescribed(e.launchBudget) &&
    moneyDescribed(e.monthlyMarketingBudget) &&
    moneyDescribed(e.targetRevenue) &&
    moneyDescribed(e.averageOrderValue);

  if (budgetsOk) completedSections.push("economics");
  else {
    if (!moneyDescribed(e.launchBudget)) {
      missingCritical.push("Бюджет запуска (точное / диапазон / unknown)");
    }
    if (!moneyDescribed(e.monthlyMarketingBudget)) {
      missingCritical.push("Месячный маркетинговый бюджет (точное / диапазон / unknown)");
    }
  }
  if (e.launchBudget.mode === "unknown") {
    assumptions.push("Бюджет запуска явно отмечен как unknown.");
  }
  if (!filled(e.criticalConstraints)) {
    missingOptional.push("Критические ограничения");
  }

  const mat = draft.materials;
  if (mat.items.length > 0 || filled(mat.websiteUrl) || filled(mat.socialProfiles)) {
    completedSections.push("materials");
  } else {
    missingOptional.push("Материалы / URL / соцпрофили");
    recommendedAdditions.push("Приложите сайт, исследования или список конкурентов, если есть.");
  }

  if (
    filled(m.geography) &&
    filled(b.geography) &&
    m.geography.trim().toLowerCase() !== b.geography.trim().toLowerCase()
  ) {
    contradictions.push(
      `География проекта («${b.geography}») отличается от географии рынка («${m.geography}»).`,
    );
  }

  if (filled(p.whatIsSold) && filled(b.ideaDescription)) {
    const idea = b.ideaDescription.toLowerCase();
    const sold = p.whatIsSold.toLowerCase();
    if (idea.length > 40 && sold.length > 40 && !idea.includes(sold.slice(0, 12)) && !sold.includes(idea.slice(0, 12))) {
      // soft signal only — not a hard block
      recommendedAdditions.push(
        "Проверьте согласованность описания идеи и формулировки «что продаётся».",
      );
    }
  }

  if (!filled(p.knownLimitations)) {
    recommendedAdditions.push("Укажите известные ограничения продукта — это ускорит risk assessment.");
  }

  const vagueIdea =
    filled(b.ideaDescription) && b.ideaDescription.trim().split(/\s+/).length < 5;
  if (vagueIdea) {
    missingCritical.push("Описание идеи слишком короткое для старта исследования");
  }

  const criticalUnresolved = missingCritical.length > 0 || contradictions.length > 2;
  const canStartResearch =
    basicsOk &&
    productCore &&
    marketGeo &&
    audienceOk &&
    moneyDescribed(e.launchBudget) &&
    moneyDescribed(e.monthlyMarketingBudget);

  let status: IntakeReadinessResult["status"];
  if (!canStartResearch || vagueIdea || criticalUnresolved && missingCritical.length >= 3) {
    status = "insufficient_data";
  } else if (
    missingCritical.length > 0 ||
    missingOptional.length >= 3 ||
    contradictions.length > 0 ||
    !productCore
  ) {
    // canStartResearch true but gaps remain
    status = missingCritical.length > 0 || !canStartResearch
      ? "insufficient_data"
      : "conditionally_ready";
  } else if (missingOptional.length > 0 || assumptions.length > 0) {
    status = "conditionally_ready";
  } else {
    status = "ready";
  }

  // Refine: if can start and only optional gaps / assumptions → conditional or ready
  if (canStartResearch && !vagueIdea && missingCritical.length === 0) {
    status =
      missingOptional.length === 0 && contradictions.length === 0 && assumptions.length === 0
        ? "ready"
        : "conditionally_ready";
  } else if (!canStartResearch || vagueIdea) {
    status = "insufficient_data";
  }

  if (status === "conditionally_ready") {
    recommendedAdditions.push(
      "Можно начать исследование — агентство отметит пробелы в brief как open questions.",
    );
  }
  if (status === "insufficient_data") {
    recommendedAdditions.push(
      "Дополните критические поля перед запуском Investigation.",
    );
  }

  return {
    status,
    completedSections,
    missingCritical,
    missingOptional,
    assumptions,
    contradictions,
    recommendedAdditions,
  };
}

/** Whether primary CTA may start investigation */
export function canStartInvestigation(result: IntakeReadinessResult): boolean {
  return result.status === "ready" || result.status === "conditionally_ready";
}
