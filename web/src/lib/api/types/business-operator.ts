import type { BusinessCampaign, CampaignControlCenter } from "@/lib/api/types/business-campaigns";

export type BusinessIntent = {
  goal: string;
  industry: string | null;
  business_type: string | null;
  campaign_type: string | null;
  confidence: number;
  recommended_scenario: string | null;
};

export type ScenarioRecommendation = {
  recommended_scenario: string;
  alternative_scenarios: string[];
  reason: string;
  confidence: number;
};

export type BusinessOperatorClarification = {
  question: string;
  reason: string;
  missing_field: string;
  options: string[];
  required: boolean;
};

export type CampaignBriefQuestion = {
  field: string;
  question: string;
  options: string[];
  required: boolean;
};

export type CampaignBriefFields = {
  business_name: string | null;
  industry: string | null;
  offer: string | null;
  target_audience: string | null;
  geography: string | null;
  channels: string[];
  budget_range: string | null;
  deadline: string | null;
  constraints: string | null;
  success_metric: string | null;
  goal: string | null;
};

export type CampaignBriefCompleteness = {
  score: number;
  threshold: number;
  passed: boolean;
  missing_questions: CampaignBriefQuestion[];
};

export type CampaignBrief = CampaignBriefFields & {
  id: string;
  owner_id: string;
  project_id: string;
  campaign_id: string | null;
  source_intent: Record<string, unknown>;
  source_scenario_id: string | null;
  status: "draft" | "confirmed" | "archived";
  completeness_score: number;
  created_at: string;
  updated_at: string;
};

export type ScenarioExplanation = {
  why_this_scenario: string;
  alternatives: string[];
  what_will_be_created: string;
  what_user_must_confirm: string;
};

export type BusinessOperatorCampaignPreview = {
  campaign_name: string;
  goal: string;
  scenario_id: string;
  scenario_name: string;
  specialists_count: number;
  expected_artifacts: string[];
};

export type BusinessOperatorAssistFields = {
  confidence_threshold: number;
  confidence_gate_passed: boolean;
  clarification_questions: BusinessOperatorClarification[];
  explanation: ScenarioExplanation | null;
  preview: BusinessOperatorCampaignPreview | null;
  intent_audit_id: string;
  message_preview: string;
  source: "rule_based" | "llm_fallback" | "clarification";
  confidence_before: number;
  confidence_after: number;
  llm_used: boolean;
  llm_provider: string | null;
  llm_model: string | null;
  brief_draft: CampaignBriefFields;
  brief_completeness: CampaignBriefCompleteness | null;
};

export type BusinessOperatorAnalyzeResponse = BusinessOperatorAssistFields & {
  intent: BusinessIntent;
  recommended_scenario: string;
  recommended_campaign_name: string;
  recommendation: ScenarioRecommendation;
};

export type BusinessOperatorClarifyResponse = BusinessOperatorAssistFields & {
  intent: BusinessIntent;
  recommended_scenario: string;
  recommended_campaign_name: string;
  recommendation: ScenarioRecommendation;
};

export type BusinessOperatorBriefResponse = {
  brief_draft: CampaignBriefFields;
  brief_completeness: CampaignBriefCompleteness;
  intent: BusinessIntent;
  recommended_scenario: string;
  recommended_campaign_name: string;
};

export type BusinessOperatorBriefConfirmResponse = BusinessOperatorBriefResponse & {
  brief: CampaignBrief;
};

export type BusinessOperatorCreateCampaignResponse = {
  campaign: BusinessCampaign;
  intent: BusinessIntent;
  recommendation: ScenarioRecommendation;
  control_center: CampaignControlCenter;
};

export type BusinessOperatorMessageInput = {
  message: string;
};

export type BusinessOperatorClarifyInput = {
  previous_intent: BusinessIntent;
  answers: Record<string, string>;
};

export type BusinessOperatorBriefInput = {
  intent: BusinessIntent;
  recommended_scenario: string;
  brief: CampaignBriefFields;
  answers?: Record<string, string>;
};

export type BusinessOperatorBriefConfirmInput = {
  intent: BusinessIntent;
  recommended_scenario: string;
  brief: CampaignBriefFields;
};

export type BusinessOperatorCreateCampaignInput = {
  message?: string;
  intent?: BusinessIntent;
  brief_id: string;
};
