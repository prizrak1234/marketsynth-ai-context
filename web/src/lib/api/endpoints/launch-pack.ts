import { apiJson } from "@/lib/api/client";
import type { BusinessIdeaValidationProjectHydration } from "@/lib/api/endpoints/business-idea-validation";
import type {
  LaunchPackOfferWorkflowStatus,
  OfferArtifactDetail,
  OfferArtifactStatus,
} from "@/lib/api/endpoints/offers";

export type LaunchPackRequestStatus =
  | "not_requested"
  | "requested"
  | "blocked"
  | "in_progress"
  | "ready"
  | "cancelled";

export type CommercialNextStepAction =
  | "prepare_launch"
  | "revise_idea"
  | "refine_inputs"
  | "request_alternative"
  | "stop_project";

export type VerdictDecisionCta = {
  action: CommercialNextStepAction;
  label_key: string;
  is_primary: boolean;
  requires_conditions_acceptance: boolean;
  requires_risk_override: boolean;
};

export type VerdictDecisionBranch = {
  verdict: string;
  headline_key: string;
  explanation: string;
  recommended_next_step_key: string;
  launch_pack_allowed: boolean;
  conditions: string[];
  primary_cta: VerdictDecisionCta | null;
  secondary_ctas: VerdictDecisionCta[];
  launch_pack_included_keys: string[];
  launch_pack_excluded_keys: string[];
};

export type CommercialNextStepDecision = {
  id: string;
  tenant_id: string;
  project_id: string;
  user_request_id: string;
  business_verdict_id: string;
  selected_action: CommercialNextStepAction;
  accepted_conditions: string[];
  override_reason?: string | null;
  created_at: string;
  updated_at: string;
};

export type LaunchPackRequest = {
  id: string;
  tenant_id: string;
  project_id: string;
  user_request_id: string;
  business_verdict_id: string;
  next_step_decision_id: string;
  status: LaunchPackRequestStatus;
  selected_next_step: CommercialNextStepAction;
  accepted_conditions: string[];
  source_verdict_type: string;
  source_confidence: number;
  offer_workflow_status?: LaunchPackOfferWorkflowStatus;
  offer_artifact_id?: string | null;
  offer_version?: number | null;
  offer_status?: OfferArtifactStatus | null;
  blocker_codes?: string[];
  next_allowed_action?: string | null;
  created_at: string;
  updated_at: string;
};

export type LaunchPackJourneyHydration = {
  project_id: string;
  user_request_id: string;
  user_request_text: string;
  validation: BusinessIdeaValidationProjectHydration;
  decision_branch: VerdictDecisionBranch;
  next_step_decision?: CommercialNextStepDecision | null;
  launch_pack_request?: LaunchPackRequest | null;
  offer?: OfferArtifactDetail | null;
  updated_at: string;
};

export type CommercialNextStepSubmitResponse = {
  decision: CommercialNextStepDecision;
  launch_pack_request?: LaunchPackRequest | null;
  offer?: OfferArtifactDetail | null;
  decision_branch: VerdictDecisionBranch;
  lineage_reused?: boolean;
};

export async function getLaunchPackJourney(
  projectId: string,
): Promise<LaunchPackJourneyHydration> {
  return apiJson<LaunchPackJourneyHydration>(`/projects/${projectId}/launch-pack/journey`);
}

export async function submitLaunchPackNextStep(
  projectId: string,
  payload: {
    selected_action: CommercialNextStepAction;
    accepted_conditions?: string[];
    override_reason?: string;
    idempotency_key: string;
  },
): Promise<CommercialNextStepSubmitResponse> {
  return apiJson<CommercialNextStepSubmitResponse>(
    `/projects/${projectId}/launch-pack/next-step`,
    {
      method: "POST",
      body: payload,
    },
  );
}
