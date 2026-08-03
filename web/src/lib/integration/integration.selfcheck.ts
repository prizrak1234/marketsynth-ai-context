/**
 * Integration I1 selfcheck.
 * Run: npx --yes tsx src/lib/integration/integration.selfcheck.ts
 */

import { mapProjectToWorkspaceView, mapProjectWithoutCampaigns } from "@/lib/integration/project-adapter";
import {
  AI591_ABSENT_CAPABILITIES,
  deriveMonitorRowsFromControlCenter,
  mapControlCenterToRuntimeMonitor,
} from "@/lib/integration/control-center-adapter";
import { FROZEN_AGENT_TYPES, ROLE_MAPPINGS } from "@/lib/integration/role-mapping";
import { normalizeIntegrationError, unavailableLabel } from "@/lib/integration/errors";
import { ApiError } from "@/lib/api/errors";
import { LOCALSTORAGE_REGISTRY } from "@/lib/integration/localstorage-registry";
import { DOMAIN_MAPPINGS } from "@/lib/integration/domain-mapping";
import type { Project } from "@/lib/api/endpoints/projects";
import type { CampaignControlCenter } from "@/lib/api/types/business-campaigns";

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}

const sampleProject: Project = {
  id: "11111111-1111-1111-1111-111111111111",
  owner_id: "22222222-2222-2222-2222-222222222222",
  name: "Sample",
  description: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T12:00:00Z",
};

{
  const view = mapProjectWithoutCampaigns(sampleProject);
  assert(view.id === sampleProject.id, "project id mapped");
  assert(view.name === "Sample", "project name mapped");
  assert(view.origin === "backend", "origin backend");
  assert(view.stageLabel === unavailableLabel(), "no invented stage");
  assert(view.nextRecommendedStep === unavailableLabel(), "no invented next step");
  assert(view.activeCampaignCount === null, "campaign count unavailable when not fetched");
  assert(view.controlCenterHref === null, "no invented CC link");
}

{
  const withCampaigns = mapProjectToWorkspaceView(sampleProject, {
    campaignSummaries: [
      {
        campaign: {
          id: "33333333-3333-3333-3333-333333333333",
          owner_id: sampleProject.owner_id,
          project_id: sampleProject.id,
          name: "Camp A",
          goal: "g",
          scenario_id: null,
          status: "active",
          metadata: {},
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
        health: {
          status: "healthy",
          blocking_reason: null,
          progress_percent: 40,
        },
        next_action_type: "approve_plan",
      },
    ],
  });
  assert(withCampaigns.activeCampaignCount === 1, "active campaign count");
  assert(withCampaigns.nextRecommendedStep.includes("approve"), "next step from CC summary");
  assert(withCampaigns.controlCenterHref?.includes("agents/chat") === true, "deep link to existing CC UI");
}

{
  const emptyList = mapProjectToWorkspaceView(sampleProject, { campaignSummaries: [] });
  assert(emptyList.activeCampaignCount === 0, "empty campaigns = 0 not invented");
}

{
  const unauthorized = normalizeIntegrationError(new ApiError("nope", 401, null));
  assert(unauthorized.loadState === "unauthorized", "401 → unauthorized");
  assert(!unauthorized.message.toLowerCase().includes("progress"), "no fake progress");
}

{
  assert(AI591_ABSENT_CAPABILITIES.length >= 4, "AI.591 gaps documented");
  assert(
    AI591_ABSENT_CAPABILITIES.some((c) => c.includes("workforce")),
    "workforce gap",
  );
}

{
  const center = {
    campaign: {
      id: "33333333-3333-3333-3333-333333333333",
      owner_id: sampleProject.owner_id,
      project_id: sampleProject.id,
      name: "Camp A",
      goal: "g",
      scenario_id: null,
      status: "active",
      metadata: {},
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    health: {
      status: "healthy",
      blocking_reason: null,
      progress_percent: 55,
    },
    next_action: {
      action_type: "approve_plan",
      label: "Approve plan",
      safe_description: "Approve the draft plan",
      resource_ids: {},
    },
    timeline: [],
    metrics: {
      plans_total: 1,
      outputs_total: 0,
      assets_total: 0,
      media_total: 0,
      packages_total: 0,
      jobs_total: 0,
      wizard_runs_total: 0,
    },
    resource_ids: {},
    safe_warnings: [],
    recovery_hint: null,
    primary_action: null,
    available_actions: [],
    tool_suggestions: [],
    skill_suggestions: [],
    latest_skill_runs: [],
    skill_context: null,
    supervisor_health_score: 90,
    supervisor_findings_count: 1,
    critical_findings_count: 0,
    top_findings: [
      {
        severity: "medium",
        category: "strategy",
        title: "Gap",
        description: "Something",
        safe_metadata: {},
      },
    ],
    workflow_suggestions: [],
    active_workflow: null,
  } as unknown as CampaignControlCenter;

  const summary = mapControlCenterToRuntimeMonitor(sampleProject.id, "Sample", center);
  assert(summary.origin === "backend", "CC summary backend origin");
  assert(summary.nextActionLabel === "Approve plan", "next action mapped");
  assert(summary.unavailableCapabilities.includes("workforce overlay"), "AI.591 gaps on summary");
  const rows = deriveMonitorRowsFromControlCenter(center);
  assert(rows.every((r) => r.origin === "backend" || r.origin === "derived"), "row origins");
  assert(!rows.some((r) => r.origin === "mock"), "CC path has no mock rows");
}

{
  for (const m of ROLE_MAPPINGS) {
    if (m.agentType) {
      assert(
        (FROZEN_AGENT_TYPES as readonly string[]).includes(m.agentType),
        `role ${m.uiRole} must use frozen AgentType`,
      );
    }
  }
  assert(FROZEN_AGENT_TYPES.length === 10, "no AgentType expansion");
}

{
  assert(LOCALSTORAGE_REGISTRY.some((k) => k.keyPattern.includes("intake_draft")), "intake key");
  assert(
    DOMAIN_MAPPINGS.some(
      (d) =>
        d.model === "BusinessVerdict" &&
        (d.classification === "D_additive_entity" || d.classification === "E_frontend_view"),
    ),
    "verdict mapped (additive or FE SoT Option C)",
  );
  assert(DOMAIN_MAPPINGS.some((d) => d.model === "AgencyRuntimeMonitor" && d.classification === "B_partial_adapter"), "monitor adapter");
}

console.log("integration I1 selfcheck OK");
