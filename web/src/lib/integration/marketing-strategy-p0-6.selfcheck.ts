/**
 * P0.6 / P1 — MarketingStrategy adapter selfcheck.
 * Run: npx --yes tsx src/lib/integration/marketing-strategy-p0-6.selfcheck.ts
 */

import type { BackendMarketingStrategyDto } from "@/lib/api/types/marketing-strategies";
import { mapBackendStrategyToProductAlpha } from "@/lib/integration/marketing-strategy-api-adapter";
import { localStrategyImportPolicy } from "@/lib/integration/marketing-strategy-sync";
import { marketingPlanDoesNotEqualStrategy } from "@/lib/integration/strategy-plan-mapping";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

assert(marketingPlanDoesNotEqualStrategy() === true, "plan ≠ strategy");
assert(localStrategyImportPolicy().autoUpload === false, "no auto upload");
assert(localStrategyImportPolicy().createsMarketingPlan === false, "no plan create");

{
  const dto: BackendMarketingStrategyDto = {
    id: "ms1",
    owner_id: "o",
    project_id: "p",
    business_verdict_id: "v1",
    business_verdict_version: 1,
    business_verdict_type: "conditional_go",
    evidence_snapshot_id: "snap1",
    evidence_snapshot_hash: "h".repeat(64),
    version: 1,
    lifecycle_status: "approved",
    strategy_origin: "rule_based_draft",
    title: "GTM",
    executive_summary: "Summary",
    primary_business_objective: "Leads",
    strategic_horizon: "90d",
    objectives: [],
    audience_segments: [],
    positioning: { category: "clinic", key_message: "Trust" },
    offers: [{ name: "Consult" }],
    channel_strategy: [{ channel: "seo" }],
    funnel: [],
    asset_plan: [],
    budget_policy: {},
    metrics: [],
    verdict_conditions: [{ verdict_condition_id: "c1" }],
    strategic_risks: [],
    assumptions: [],
    execution_constraints: ["budget unknown"],
    readiness_status: "conditionally_ready",
    related_marketing_plan_ids: [],
    handoff_status: "not_started",
    creates_marketing_plan: false,
    creates_campaign: false,
    creates_execution_approval: false,
    creates_agent_run: false,
    is_marketing_plan: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  const view = mapBackendStrategyToProductAlpha(dto, "Clinic");
  assert(view.status === "approved", "status map");
  assert(view.verdictId === "v1", "verdict pin");
  assert(view.verdictVersion === 1, "verdict version pin");
  assert(view.evidenceSnapshotId === "snap1", "snapshot pin");
  assert(view.localMockLabel === "", "no mock label on backend map");
}

console.log("marketing-strategy-p0-6.selfcheck: OK");
