/**
 * P0.1 — ProductIntakeDraft ↔ ProjectBrief mapping.
 */

import type { ProjectBriefCreateBody, ProjectBriefDto } from "@/lib/api/types/project-briefs";
import type {
  MoneyValue,
  ProjectIntakeDraft,
  IntakeReadinessStatus,
} from "@/lib/project-intake/types";

function moneyToDto(m: MoneyValue): {
  mode: string;
  exact?: string | null;
  min?: string | null;
  max?: string | null;
} {
  return {
    mode: m.mode,
    exact: m.mode === "exact" ? m.exact ?? null : null,
    min: m.mode === "range" ? m.min ?? null : null,
    max: m.mode === "range" ? m.max ?? null : null,
  };
}

function moneyFromDto(raw: unknown): MoneyValue {
  if (!raw || typeof raw !== "object") return { mode: "unknown" };
  const o = raw as Record<string, unknown>;
  const mode = o.mode === "exact" || o.mode === "range" || o.mode === "unknown" ? o.mode : "unknown";
  return {
    mode,
    exact: typeof o.exact === "string" ? o.exact : undefined,
    min: typeof o.min === "string" ? o.min : undefined,
    max: typeof o.max === "string" ? o.max : undefined,
  };
}

function readinessMap(
  status: IntakeReadinessStatus | null | undefined,
): ProjectBriefCreateBody["readiness_status"] {
  if (status === "ready") return "ready";
  if (status === "conditionally_ready") return "conditionally_ready";
  return "insufficient_data";
}

/**
 * Map full local intake → typed ProjectBrief create/update body.
 * Materials: metadata only (no file contents).
 */
export function mapIntakeDraftToBriefCreate(draft: ProjectIntakeDraft): ProjectBriefCreateBody {
  const b = draft.projectBasics;
  const p = draft.product;
  const m = draft.market;
  const a = draft.audience;
  const e = draft.economics;
  const mat = draft.materials;
  const readiness = draft.readiness;

  return {
    language: b.interfaceLanguage || "ru",
    project_basics: {
      project_name: b.name,
      idea_description: b.ideaDescription,
      business_type: b.businessType || "",
      project_stage: b.projectStage || "",
      geography: b.geography,
      preferred_language: b.interfaceLanguage || "ru",
    },
    product: {
      product_or_service: p.whatIsSold,
      customer_problem: p.primaryProblem,
      value_proposition: p.valueProposition,
      price: moneyToDto(p.priceUnknown ? { mode: "unknown" } : p.price),
      price_type: p.price.mode,
      price_value: p.price.exact ?? null,
      price_min: p.price.min ?? null,
      price_max: p.price.max ?? null,
      delivery_model: p.deliveryUnknown ? "" : p.deliveryModel,
      differentiators: p.differentiators,
      limitations: p.knownLimitations,
    },
    market: {
      target_market: m.targetMarket,
      geography: m.geography,
      known_competitors: m.competitorsUnknown ? "" : m.knownCompetitors,
      competitor_urls: m.competitorUrls,
      market_assumptions: m.marketAssumptions,
      demand_evidence: m.demandUnavailable ? "" : m.demandEvidence,
      seasonality: m.seasonality,
      restrictions: m.restrictions,
    },
    audience: {
      business_model: a.customerModel,
      segments: a.segments.map((s) => ({
        id: s.id,
        label: s.label,
        notes: s.notes,
      })),
      decision_maker: a.decisionMaker,
      buyer_user_distinction: a.buyerUserDistinction,
      geography: a.customerLocation,
      pains: a.expectedPains,
      objections: a.expectedObjections,
      current_research: a.currentResearch,
    },
    economics: {
      launch_budget: moneyToDto(e.launchBudget),
      monthly_marketing_budget: moneyToDto(e.monthlyMarketingBudget),
      target_revenue: moneyToDto(e.targetRevenue),
      payback_period: e.paybackUnknown ? "" : e.paybackPeriod,
      average_order_value: moneyToDto(e.averageOrderValue),
      gross_margin: e.grossMarginUnknown ? "" : e.grossMargin,
      team_size: e.teamSizeUnknown ? "" : e.teamSize,
      internal_resources: e.internalResources,
      launch_deadline: e.launchDeadlineUnknown ? "" : e.launchDeadline,
      critical_constraints: e.criticalConstraints,
    },
    materials_summary: {
      website_url: mat.websiteUrl,
      social_profiles: mat.socialProfiles,
      items: mat.items.map((item) => ({
        title: item.label,
        type: item.kind,
        filename: null,
        url: null,
        local_reference_label: item.id,
        status: "noted",
        notes: item.note ?? null,
      })),
    },
    assumptions: [
      ...draft.assumptions,
      ...(readiness?.assumptions ?? []),
    ].filter(Boolean),
    missing_data: [
      ...draft.missingData,
      ...(readiness?.missingCritical ?? []),
    ].filter(Boolean),
    readiness_status: readinessMap(readiness?.status),
    readiness_reasons: [
      ...(readiness?.missingCritical ?? []),
      ...(readiness?.contradictions ?? []),
    ],
  };
}

export type BriefFieldLoss = {
  field: string;
  reason: string;
};

/** Detect intentional omissions / FE-only fields not first-class on backend. */
export function detectBriefFieldLoss(draft: ProjectIntakeDraft): BriefFieldLoss[] {
  const losses: BriefFieldLoss[] = [];
  if (draft.currentStep) {
    losses.push({
      field: "currentStep",
      reason: "wizard UI state — not persisted on ProjectBrief",
    });
  }
  if (draft.materials.items.some((i) => i.note && i.note.length > 0)) {
    /* notes are persisted */
  }
  losses.push({
    field: "materials.file_content",
    reason: "file binaries intentionally unsupported in P0.1",
  });
  losses.push({
    field: "backendSync / local ids",
    reason: "frontend integration metadata excluded from fingerprint",
  });
  return losses;
}

export function projectBriefEqualsCampaignBrief(): false {
  return false;
}

export function mapBriefDtoOverlay(brief: ProjectBriefDto): {
  projectName: string;
  ideaDescription: string;
  fingerprint: string;
  version: number;
  status: string;
} {
  const basics = brief.project_basics as Record<string, unknown>;
  return {
    projectName: String(basics.project_name ?? ""),
    ideaDescription: String(basics.idea_description ?? ""),
    fingerprint: brief.input_fingerprint,
    version: brief.version,
    status: brief.status,
  };
}

export { moneyFromDto };
