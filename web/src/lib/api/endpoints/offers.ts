import { apiJson } from "@/lib/api/client";

export type OfferArtifactStatus =
  | "requested"
  | "generating"
  | "generated"
  | "review_required"
  | "approved"
  | "rejected"
  | "revision_requested"
  | "failed"
  | "cancelled";

export type OfferApprovalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "revision_requested";

export type LaunchPackOfferWorkflowStatus =
  | "not_started"
  | "requested"
  | "building_offer"
  | "offer_review_required"
  | "offer_approved"
  | "ready_for_next_stage"
  | "blocked_by_verdict"
  | "blocked_by_missing_positioning"
  | "blocked_by_claims"
  | "blocked_by_evidence"
  | "offer_generation_failed"
  | "offer_rejected"
  | "revision_required";

export type UpstreamSourceMode = "native_skill_output" | "bridged_biv_snapshot";

export type UpstreamSnapshotSummary = {
  artifact_type: string;
  source_skill_id: string;
  source_skill_version: string;
  source_mode: UpstreamSourceMode;
  bridge_version?: string | null;
  source_biv_id?: string | null;
  source_biv_hash?: string | null;
  generated_from_fields: string[];
  limitations: string[];
  replacement_required: boolean;
  source_output_hash: string;
};

export type OfferArtifactDetail = {
  id: string;
  launch_pack_request_id: string;
  project_id: string;
  skill_id: string;
  skill_version: string;
  status: OfferArtifactStatus;
  approval_status: OfferApprovalStatus;
  version_number: number;
  offer_title: string;
  offer_summary: string;
  human_review_required: boolean;
  output_hash: string;
  blocker_code?: string | null;
  created_at: string;
  updated_at: string;
  approved_at?: string | null;
  problem_statement: string;
  promised_outcome: string;
  value_proposition: string;
  offer_components: string[];
  proof_references: string[];
  objection_handling: Array<Record<string, unknown>>;
  conditions: string[];
  limitations: string[];
  cta: string;
  unsupported_claims: string[];
  evidence_gaps: string[];
  target_segment_ids: string[];
  preferred_offer_id?: string | null;
  offer_readiness: string;
  revision_of_id?: string | null;
  lineage_metadata: Record<string, unknown>;
  upstream_sources?: UpstreamSnapshotSummary[];
};

export type OfferVersionHistoryItem = {
  id: string;
  version_number: number;
  status: OfferArtifactStatus;
  output_hash: string;
  offer_title: string;
  created_at: string;
  approval_status: OfferApprovalStatus;
};

export async function getLaunchPackOffer(
  projectId: string,
  launchPackId: string,
): Promise<OfferArtifactDetail> {
  return apiJson<OfferArtifactDetail>(
    `/projects/${projectId}/launch-packs/${launchPackId}/offer`,
  );
}

export async function approveOffer(
  projectId: string,
  offerId: string,
  payload: { expected_output_hash: string; comment?: string },
): Promise<OfferArtifactDetail> {
  return apiJson<OfferArtifactDetail>(`/projects/${projectId}/offers/${offerId}/approve`, {
    method: "POST",
    body: payload,
  });
}

export async function rejectOffer(
  projectId: string,
  offerId: string,
  payload: { expected_output_hash: string; comment?: string },
): Promise<OfferArtifactDetail> {
  return apiJson<OfferArtifactDetail>(`/projects/${projectId}/offers/${offerId}/reject`, {
    method: "POST",
    body: payload,
  });
}

export async function requestOfferRevision(
  projectId: string,
  offerId: string,
  payload: { expected_output_hash: string; comment: string },
): Promise<OfferArtifactDetail> {
  return apiJson<OfferArtifactDetail>(
    `/projects/${projectId}/offers/${offerId}/request-revision`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export async function listOfferVersions(
  projectId: string,
  offerId: string,
): Promise<OfferVersionHistoryItem[]> {
  return apiJson<OfferVersionHistoryItem[]>(
    `/projects/${projectId}/offers/${offerId}/versions`,
  );
}
