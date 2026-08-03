/**
 * Commercial MVP P0.1 — ProjectBrief mapping selfcheck.
 * Run: npx --yes tsx src/lib/integration/project-brief.selfcheck.ts
 */

import {
  detectBriefFieldLoss,
  mapIntakeDraftToBriefCreate,
  projectBriefEqualsCampaignBrief,
} from "@/lib/integration/project-brief-adapter";
import { reconcileBriefFingerprints } from "@/lib/integration/project-brief-reconciliation";
import { DOMAIN_MAPPINGS } from "@/lib/integration/domain-mapping";
import type { ProjectIntakeDraft } from "@/lib/project-intake/types";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

const sample = {
  id: "d1",
  projectBasics: {
    name: "Clinic",
    ideaDescription: "Leads",
    businessType: "local_business",
    projectStage: "preparing_launch",
    geography: "Moscow",
    interfaceLanguage: "ru",
  },
  product: {
    whatIsSold: "Service",
    primaryProblem: "Pain",
    valueProposition: "Value",
    price: { mode: "unknown" },
    deliveryModel: "offline",
    differentiators: "x",
    knownLimitations: "y",
    priceUnknown: true,
    deliveryUnknown: false,
  },
  market: {
    targetMarket: "t",
    geography: "g",
    knownCompetitors: "",
    competitorUrls: "",
    marketAssumptions: "a",
    demandEvidence: "",
    seasonality: "",
    restrictions: "",
    competitorsUnknown: true,
    demandUnavailable: true,
    marketSizeUnknown: true,
  },
  audience: {
    customerModel: "b2c",
    segments: [{ id: "1", label: "Seg", notes: "" }],
    decisionMaker: "Patient",
    buyerUserDistinction: "same",
    customerLocation: "Moscow",
    expectedPains: "p",
    expectedObjections: "o",
    currentResearch: "r",
  },
  economics: {
    launchBudget: { mode: "range", min: "1", max: "2" },
    monthlyMarketingBudget: { mode: "unknown" },
    targetRevenue: { mode: "exact", exact: "10" },
    paybackPeriod: "6m",
    paybackUnknown: false,
    averageOrderValue: { mode: "unknown" },
    grossMargin: "",
    grossMarginUnknown: true,
    teamSize: "3",
    teamSizeUnknown: false,
    internalResources: "team",
    launchDeadline: "",
    launchDeadlineUnknown: true,
    criticalConstraints: "c",
  },
  materials: {
    websiteUrl: "https://x.test",
    socialProfiles: "@x",
    items: [{ id: "m1", kind: "document", label: "Doc", note: "meta" }],
  },
  assumptions: ["a1"],
  missingData: ["cac"],
  readiness: {
    status: "conditionally_ready",
    completedSections: ["basics"],
    missingCritical: ["cac"],
    missingOptional: [],
    assumptions: ["a1"],
    contradictions: [],
    recommendedAdditions: [],
  },
  currentStep: "review",
  updatedAt: "2026-01-01T00:00:00.000Z",
} as unknown as ProjectIntakeDraft;

{
  assert(projectBriefEqualsCampaignBrief() === false, "≠ CampaignBrief");
  const body = mapIntakeDraftToBriefCreate(sample);
  assert(body.project_basics.project_name === "Clinic", "name mapped");
  const price = body.product.price as { mode: string };
  const monthly = body.economics.monthly_marketing_budget as { mode: string };
  const launch = body.economics.launch_budget as { mode: string };
  const items = body.materials_summary.items as Array<Record<string, unknown>>;
  assert(price.mode === "unknown", "unknown money");
  assert(monthly.mode === "unknown", "econ unknown");
  assert(launch.mode === "range", "range preserved");
  assert(items[0]?.local_reference_label === "m1", "material meta");
  assert(!("content" in (items[0] ?? {})), "no file content");
  assert(body.readiness_status === "conditionally_ready", "readiness");
  const losses = detectBriefFieldLoss(sample);
  assert(losses.some((l) => l.field.includes("file_content")), "file content loss noted");
}

{
  const equal = reconcileBriefFingerprints({
    localFingerprint: "abc",
    backend: {
      id: "b1",
      owner_id: "o",
      project_id: "p",
      version: 1,
      status: "submitted",
      language: "ru",
      project_basics: {},
      product: {},
      market: {},
      audience: {},
      economics: {},
      materials_summary: {},
      assumptions: [],
      missing_data: [],
      readiness_status: "ready",
      readiness_reasons: [],
      input_fingerprint: "abc",
      supersedes_brief_id: null,
      submitted_at: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    localUpdatedAt: "2026-01-01T00:00:00Z",
  });
  assert(equal.case === "equal_fingerprint", "equal");
  assert(equal.autoMerge === false, "no silent merge");
}

{
  const row = DOMAIN_MAPPINGS.find((d) => d.model === "ProjectBrief");
  assert(row?.classification === "A_direct", "ProjectBrief SoT");
  assert(!DOMAIN_MAPPINGS.some((d) => d.notes.toLowerCase().includes("botfazer") && d.model === "ProjectBrief"), "brand");
}

console.log("project-brief.selfcheck.ts: OK");
