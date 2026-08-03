/**
 * Centralized UI role → backend AgentType / specialist mapping.
 * I1: NO new AgentType values. Aliases are presentation-only.
 */

export type UiAgencyRole =
  | "CEO"
  | "Research Director"
  | "Market Analyst"
  | "Competitor Analyst"
  | "Audience Analyst"
  | "Risk Officer"
  | "Chief Marketing Strategist"
  | "Performance Marketer"
  | "Content Strategist"
  | "Copywriter"
  | "Designer"
  | "Analyst"
  | "Project Manager"
  | "Client Owner";

/** Existing backend AgentType string values — do not extend here. */
export type BackendAgentType =
  | "general"
  | "programmer"
  | "media"
  | "strategist"
  | "researcher"
  | "copywriter"
  | "content_planner"
  | "critic"
  | "analyst"
  | "orchestrator";

export type BackendSpecialistType =
  | "strategist"
  | "researcher"
  | "copywriter"
  | "content_planner"
  | "analyst"
  | "critic"
  | "offer_strategist"
  | "funnel_architect"
  | "lead_magnet_specialist"
  | "sales_copywriter"
  | "email_dm_specialist"
  | "cro_specialist"
  | "smm_strategist"
  | "ad_creative_strategist";

export type RoleMappingKind =
  | "exact_backend_match"
  | "frontend_alias"
  | "aggregate_ui_role"
  | "unsupported"
  | "future_backend_gap";

export type RoleMappingEntry = {
  uiRole: UiAgencyRole;
  displayLabel: string;
  agentType: BackendAgentType | null;
  specialistType: BackendSpecialistType | null;
  kind: RoleMappingKind;
  notes: string;
};

export const ROLE_MAPPINGS: readonly RoleMappingEntry[] = [
  {
    uiRole: "CEO",
    displayLabel: "CEO",
    agentType: null,
    specialistType: null,
    kind: "aggregate_ui_role",
    notes: "Tenant governance label — maps to owner/user, never AgentType",
  },
  {
    uiRole: "Client Owner",
    displayLabel: "Client Owner",
    agentType: null,
    specialistType: null,
    kind: "aggregate_ui_role",
    notes: "Maps to UserRole.OWNER / project owner_id — not AgentType",
  },
  {
    uiRole: "Research Director",
    displayLabel: "Research Director",
    agentType: "orchestrator",
    specialistType: "researcher",
    kind: "frontend_alias",
    notes: "UI RACI over researcher/orchestrator — not a new AgentType",
  },
  {
    uiRole: "Market Analyst",
    displayLabel: "Market Analyst",
    agentType: "analyst",
    specialistType: "analyst",
    kind: "frontend_alias",
    notes: "Alias of analyst (+ tools)",
  },
  {
    uiRole: "Competitor Analyst",
    displayLabel: "Competitor Analyst",
    agentType: "analyst",
    specialistType: "researcher",
    kind: "frontend_alias",
    notes: "Presentation facet of researcher/analyst",
  },
  {
    uiRole: "Audience Analyst",
    displayLabel: "Audience Analyst",
    agentType: "analyst",
    specialistType: "researcher",
    kind: "frontend_alias",
    notes: "Presentation facet of researcher/analyst",
  },
  {
    uiRole: "Risk Officer",
    displayLabel: "Risk Officer",
    agentType: "critic",
    specialistType: "critic",
    kind: "frontend_alias",
    notes: "Closest to critic / supervisor findings owner — not AI.591 workforce",
  },
  {
    uiRole: "Chief Marketing Strategist",
    displayLabel: "Chief Marketing Strategist",
    agentType: "strategist",
    specialistType: "strategist",
    kind: "exact_backend_match",
    notes: "Aligns with strategist AgentType / MarketingSpecialistType",
  },
  {
    uiRole: "Performance Marketer",
    displayLabel: "Performance Marketer",
    agentType: null,
    specialistType: "ad_creative_strategist",
    kind: "frontend_alias",
    notes: "Closest specialist: ad_creative_strategist; no AgentType expansion",
  },
  {
    uiRole: "Content Strategist",
    displayLabel: "Content Strategist",
    agentType: "content_planner",
    specialistType: "content_planner",
    kind: "exact_backend_match",
    notes: "content_planner",
  },
  {
    uiRole: "Copywriter",
    displayLabel: "Copywriter",
    agentType: "copywriter",
    specialistType: "copywriter",
    kind: "exact_backend_match",
    notes: "Exact",
  },
  {
    uiRole: "Designer",
    displayLabel: "Designer",
    agentType: "media",
    specialistType: null,
    kind: "frontend_alias",
    notes: "Closest AgentType.media — UI label only",
  },
  {
    uiRole: "Analyst",
    displayLabel: "Analyst",
    agentType: "analyst",
    specialistType: "analyst",
    kind: "exact_backend_match",
    notes: "Exact",
  },
  {
    uiRole: "Project Manager",
    displayLabel: "Project Manager",
    agentType: "orchestrator",
    specialistType: null,
    kind: "frontend_alias",
    notes: "Orchestration facet — not new AgentType",
  },
] as const;

export function getRoleMapping(uiRole: string): RoleMappingEntry | null {
  return ROLE_MAPPINGS.find((r) => r.uiRole === uiRole) ?? null;
}

/** Frozen list of backend AgentType — I1 must not add to this. */
export const FROZEN_AGENT_TYPES: readonly BackendAgentType[] = [
  "general",
  "programmer",
  "media",
  "strategist",
  "researcher",
  "copywriter",
  "content_planner",
  "critic",
  "analyst",
  "orchestrator",
] as const;
