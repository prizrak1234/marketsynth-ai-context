/**
 * Map ProductIntakeDraft → AnalysisContextFields for BIV commercial path.
 */

import type { AnalysisContextFields } from "@/lib/api/endpoints/analysis-contexts";
import { evaluateAnalysisContextSpecificity } from "@/lib/biv/analysis-context-specificity";
import type { MoneyValue, ProjectIntakeDraft } from "@/lib/project-intake/types";

const DEFAULT_ANALYSIS_GOAL = "Проверить жизнеспособность бизнес-идеи перед запуском";

function formatMoney(m: MoneyValue, unknownFlag?: boolean): string | null {
  if (unknownFlag || m.mode === "unknown") {
    return "неизвестно";
  }
  if (m.mode === "exact") {
    return m.exact?.trim() || null;
  }
  if (m.mode === "range") {
    const min = m.min?.trim();
    const max = m.max?.trim();
    if (min && max) return `${min}–${max}`;
    return min || max || null;
  }
  return null;
}

function audienceLabel(draft: ProjectIntakeDraft): string {
  const segments = draft.audience.segments
    .map((segment) => segment.label.trim())
    .filter(Boolean);
  if (segments.length > 0) {
    return segments.join("; ");
  }
  const pains = draft.audience.expectedPains.trim();
  if (pains) {
    return pains;
  }
  return "";
}

function geographyLabel(draft: ProjectIntakeDraft): string {
  const marketGeo = draft.market.geography.trim();
  const basicsGeo = draft.projectBasics.geography.trim();
  return marketGeo || basicsGeo;
}

function budgetLabel(draft: ProjectIntakeDraft): string | null {
  const launch = formatMoney(
    draft.economics.launchBudget,
    draft.economics.launchBudget.mode === "unknown",
  );
  const monthly = formatMoney(
    draft.economics.monthlyMarketingBudget,
    draft.economics.monthlyMarketingBudget.mode === "unknown",
  );
  const parts = [
    launch ? `launch: ${launch}` : null,
    monthly ? `marketing/month: ${monthly}` : null,
    draft.economics.criticalConstraints.trim()
      ? `constraints: ${draft.economics.criticalConstraints.trim()}`
      : null,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join("; ") : null;
}

export function mapIntakeDraftToAnalysisContextFields(
  draft: ProjectIntakeDraft,
): AnalysisContextFields {
  const geography = geographyLabel(draft);
  const targetCustomer = audienceLabel(draft);
  const pricing = formatMoney(draft.product.price, draft.product.priceUnknown);
  const competitors = draft.market.competitorsUnknown
    ? "неизвестно"
    : draft.market.knownCompetitors.trim() || draft.market.competitorUrls.trim() || null;

  return {
    idea_description: draft.projectBasics.ideaDescription.trim(),
    product_or_service: draft.product.whatIsSold.trim() || draft.projectBasics.ideaDescription.trim(),
    target_customer: targetCustomer || null,
    geography: geography || null,
    business_model: draft.projectBasics.businessType || draft.product.deliveryModel.trim() || null,
    pricing_or_revenue_model: pricing,
    current_stage: draft.projectBasics.projectStage || null,
    budget_context: budgetLabel(draft),
    known_competitors: competitors,
    analysis_goal: DEFAULT_ANALYSIS_GOAL,
    target_customer_unknown: !targetCustomer,
    geography_unknown: !geography,
  };
}

export function intakeDraftMeetsAnalysisContextGate(draft: ProjectIntakeDraft): {
  ok: boolean;
  fields: AnalysisContextFields;
  missing_fields: string[];
  warnings: string[];
} {
  const fields = mapIntakeDraftToAnalysisContextFields(draft);
  const evaluation = evaluateAnalysisContextSpecificity(fields);
  return {
    ok: evaluation.can_confirm,
    fields,
    missing_fields: evaluation.missing_fields,
    warnings: evaluation.warnings,
  };
}
