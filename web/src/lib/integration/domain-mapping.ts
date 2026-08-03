/**
 * Product Alpha domain → backend mapping classes (contracts only; no new tables in I1).
 */

import type { DomainMappingClass } from "@/lib/integration/contracts";

export type DomainMappingEntry = {
  model: string;
  classification: DomainMappingClass;
  backendTouchpoints: string[];
  notes: string;
};

export const DOMAIN_MAPPINGS: readonly DomainMappingEntry[] = [
  {
    model: "ProjectIntakeDraft",
    classification: "C_multiple",
    backendTouchpoints: ["Project", "ProjectBrief"],
    notes:
      "P0.1: full structured intake → ProjectBrief SoT. Project still identity + name/description. CampaignBrief remains separate operator entity.",
  },
  {
    model: "ProjectBrief",
    classification: "A_direct",
    backendTouchpoints: ["project_briefs"],
    notes:
      "Commercial MVP P0.1 durable versioned intake. Not CampaignBrief. No Investigation/AgentRun side effects.",
  },
  {
    model: "InvestigationWorkspace",
    classification: "B_partial_adapter",
    backendTouchpoints: [
      "Project",
      "CampaignControlCenter",
      "CampaignSupervisorReport",
      "MarketingSkillRun (research artifact candidates)",
    ],
    notes:
      "I3 Option B: projections only. EvidenceRecord/Source absent — do not promote Supervisor/LLM to evidence. Additive Investigation domain documented for later approval.",
  },
  {
    model: "BusinessVerdict",
    classification: "A_backend_sot",
    backendTouchpoints: [
      "BusinessVerdict + EvidenceSnapshot + VerdictEvidenceLink (P0.5)",
      "VerdictKind vocabulary",
    ],
    notes:
      "P0.5: durable BusinessVerdict SoT on immutable Evidence snapshots. Readiness ≠ verdict. Approval ≠ execution. No auto Strategy. Supervisor/CC remain separate.",
  },
  {
    model: "MarketingStrategy",
    classification: "A_backend_sot",
    backendTouchpoints: [
      "MarketingStrategy (P0.6) linked to approved BusinessVerdict",
      "MarketingPlan remains separate ops spine",
    ],
    notes:
      "P0.6: durable GTM Strategy SoT. MarketingStrategy ≠ MarketingPlan. Eligible only from approved GO/CONDITIONAL_GO. No auto plan/campaign/execution.",
  },
  {
    model: "MarketingPlan",
    classification: "A_direct",
    backendTouchpoints: ["MarketingPlan", "MarketingPlanVersion", "execution runs"],
    notes: "Project-scoped ops/execution plan SoT — goal + specialist_tasks. Not GTM Strategy.",
  },
  {
    model: "ImplementationPlan",
    classification: "B_partial_adapter",
    backendTouchpoints: ["MarketingPlan (ops projection only)", "approvals (boundary)", "execution services (deferred)"],
    notes:
      "I6 Option B: higher-level delivery plan (local / future domain). MarketingPlan = specialist-task projection SoT. Read-only handoff preview; draft write blocked (no create API). Never equate task→AgentRun.",
  },
  {
    model: "WorkspaceSnapshot",
    classification: "E_frontend_view",
    backendTouchpoints: ["Project", "CampaignControlCenter", "Supervisor"],
    notes: "Composed view — never persist as own table",
  },
  {
    model: "AgencyRuntimeMonitor",
    classification: "B_partial_adapter",
    backendTouchpoints: ["CampaignControlCenter"],
    notes: "Projection only; AI.591 overlay absent",
  },
] as const;
