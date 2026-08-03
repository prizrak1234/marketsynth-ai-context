export type MarketingSkillType =
  | "segment_research"
  | "meaning_unpacking"
  | "offer_packaging"
  | "offer_justification"
  | "wordstat_research"
  | "metrica_analysis"
  | "visual_report";

export type MarketingSkillRunStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export type MarketingSkillSuggestion = {
  skill_type: MarketingSkillType;
  label: string;
  safe_description: string;
  recommended: boolean;
};

export type MarketingSkillDefinition = {
  skill_type: MarketingSkillType;
  name: string;
  purpose: string;
  required_inputs: string[];
  optional_tools: string[];
  output_type: string;
  out_of_scope: string[];
};

export type MarketingSkillRun = {
  id: string;
  owner_id: string;
  project_id: string;
  campaign_id?: string | null;
  skill_type: MarketingSkillType;
  status: MarketingSkillRunStatus;
  input_payload: Record<string, unknown>;
  output_payload?: Record<string, unknown> | null;
  used_tool_call_ids: string[];
  safe_metadata: Record<string, unknown>;
  error?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
};

export type CreateMarketingSkillRunInput = {
  input_payload?: Record<string, unknown>;
  campaign_id?: string | null;
};
