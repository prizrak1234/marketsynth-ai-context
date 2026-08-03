/** Marketing specialist pipeline groups and dependency hints (AI.120). */

export type SpecialistSlug =
  | "strategist"
  | "researcher"
  | "content_planner"
  | "copywriter"
  | "critic"
  | "analyst"
  | "offer_strategist"
  | "funnel_architect"
  | "lead_magnet_specialist"
  | "sales_copywriter"
  | "email_dm_specialist"
  | "cro_specialist"
  | "smm_strategist"
  | "ad_creative_strategist";

export type PipelineGroupId = "frozen" | "offer_funnel" | "social_ads_cro";

export type PipelineGroup = {
  id: PipelineGroupId;
  label: string;
  specialists: SpecialistSlug[];
};

export const PIPELINE_GROUPS: PipelineGroup[] = [
  {
    id: "frozen",
    label: "Frozen pipeline",
    specialists: [
      "strategist",
      "researcher",
      "content_planner",
      "copywriter",
      "critic",
      "analyst",
    ],
  },
  {
    id: "offer_funnel",
    label: "Offer / Funnel pipeline",
    specialists: [
      "offer_strategist",
      "funnel_architect",
      "lead_magnet_specialist",
      "sales_copywriter",
      "email_dm_specialist",
    ],
  },
  {
    id: "social_ads_cro",
    label: "Social / Ads / CRO pipeline",
    specialists: ["cro_specialist", "smm_strategist", "ad_creative_strategist"],
  },
];

/** Mirrors backend V2 + frozen dependency messages for disabled execute buttons. */
export const DEPENDENCY_ERROR_MESSAGES: Record<string, Record<string, string>> = {
  researcher: { strategist: "Requires completed Strategist output" },
  content_planner: {
    strategist: "Requires completed Strategist output",
    researcher: "Requires completed Researcher output",
  },
  copywriter: {
    strategist: "Requires completed Strategist output",
    researcher: "Requires completed Researcher output",
    content_planner: "Requires completed Content Planner output",
  },
  critic: {
    strategist: "Requires completed Strategist output",
    researcher: "Requires completed Researcher output",
    content_planner: "Requires completed Content Planner output",
    copywriter: "Requires completed Copywriter output",
  },
  analyst: {
    strategist: "Requires completed Strategist output",
    researcher: "Requires completed Researcher output",
    content_planner: "Requires completed Content Planner output",
    copywriter: "Requires completed Copywriter output",
    critic: "Requires completed Critic output",
  },
  offer_strategist: {
    strategist: "Requires completed Strategist output",
    researcher: "Requires completed Researcher output",
  },
  funnel_architect: {
    strategist: "Requires completed Strategist output",
    researcher: "Requires completed Researcher output",
    offer_strategist: "Requires completed Offer Strategist output",
  },
  lead_magnet_specialist: {
    offer_strategist: "Requires completed Offer Strategist output",
    funnel_architect: "Requires completed Funnel Architect output",
  },
  sales_copywriter: {
    offer_strategist: "Requires completed Offer Strategist output",
    researcher: "Requires completed Researcher output",
  },
  email_dm_specialist: {
    offer_strategist: "Requires completed Offer Strategist output",
    sales_copywriter: "Requires completed Sales Copywriter output",
  },
  cro_specialist: {
    offer_strategist: "Requires completed Offer Strategist output",
    funnel_architect: "Requires completed Funnel Architect output",
    sales_copywriter: "Requires completed Sales Copywriter output",
  },
  smm_strategist: {
    strategist: "Requires completed Strategist output",
    researcher: "Requires completed Researcher output",
    content_planner: "Requires completed Content Planner output",
    offer_strategist: "Requires completed Offer Strategist output",
  },
  ad_creative_strategist: {
    offer_strategist: "Requires completed Offer Strategist output",
    researcher: "Requires completed Researcher output",
    sales_copywriter: "Requires completed Sales Copywriter output",
  },
};

const EXECUTABLE_SPECIALISTS = new Set<string>([
  ...PIPELINE_GROUPS.flatMap((g) => g.specialists),
]);

export function pipelineGroupForSpecialist(specialist: string): PipelineGroup | undefined {
  return PIPELINE_GROUPS.find((group) => group.specialists.includes(specialist as SpecialistSlug));
}

export function isExecutableSpecialist(specialist: string): boolean {
  return EXECUTABLE_SPECIALISTS.has(specialist);
}

export function firstMissingDependencyMessage(
  specialist: string,
  completed: Set<string>,
): string | null {
  const deps = Object.keys(DEPENDENCY_ERROR_MESSAGES[specialist] ?? {});
  for (const dep of deps) {
    if (!completed.has(dep)) {
      return DEPENDENCY_ERROR_MESSAGES[specialist][dep] ?? `Requires completed ${dep} output`;
    }
  }
  return null;
}

export function specialistDisplayName(specialist: string): string {
  return specialist.replace(/_/g, " ");
}
