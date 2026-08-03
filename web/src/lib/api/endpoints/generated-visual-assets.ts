/** Generated visual assets API (Phase H2.6A / H2.8E). */

import { apiJson } from "@/lib/api/client";

export type GeneratedVisualAssetDto = {
  id: string;
  owner_id: string;
  user_request_id: string;
  skill_code: string;
  skill_version: string;
  provider: string;
  model: string | null;
  provider_model?: string | null;
  generation_mode: "real" | "mock";
  asset_type: "user_result" | "diagnostic_placeholder" | "video_clip";
  prompt_summary: string;
  aspect_ratio: string;
  width: number | null;
  height: number | null;
  mime_type: string;
  storage_uri: string | null;
  checksum: string | null;
  status: string;
  safety_result: string | null;
  created_at: string;
  user_accepted?: boolean | null;
  review_notes?: string | null;
  parent_asset_id?: string | null;
};

export type ImageGenerationReadinessDto = {
  image_generation_enabled: boolean;
  configured_provider: string;
  provider_ready: boolean;
  real_generation_available: boolean;
  mock_only: boolean;
  can_generate_user_result: boolean;
  can_generate_diagnostic?: boolean;
  allow_mock_image_results?: boolean;
  openai_images_configured?: boolean;
  can_generate?: boolean;
  identity_execution_mode?: string;
  identity_ab_harness_enabled?: boolean;
  identity_max_images?: number;
  subsystem?: string;
  identity_provider?: string;
  identity_capability_status?: string;
  identity_provider_input_capacity?: number;
  supports_supporting_references?: boolean;
  paid_approval_required?: boolean;
  identity_safe_summary?: string | null;
};

export type IdentitySubsystemReadinessDto = {
  ready: boolean;
  safe_summary: string;
  safe_detail_lines: string[];
  provider?: string | null;
  capability_status?: string;
  uploaded_references?: number;
  selected_identity_references?: number;
  selected_style_references?: number;
  references_provider_will_receive?: number;
  actual_provider_input_capacity?: number;
  paid_approval_required?: boolean;
  paid_approval_granted?: boolean;
  estimated_provider_calls?: number;
  mock_or_real?: string;
  blocking_conditions?: Array<{
    code: string;
    blocking: boolean;
    safe_message: string;
    ok: boolean;
  }>;
  manifest_preview?: {
    stored_count: number;
    identity_selected: number;
    style_selected: number;
    transmitted_count: number;
    safe_transmit_note?: string | null;
  };
};

export async function getGeneratedVisualAsset(
  assetId: string,
): Promise<GeneratedVisualAssetDto> {
  return apiJson<GeneratedVisualAssetDto>(`/generated-visual-assets/${assetId}`);
}

export async function listGeneratedVisualAssets(
  limit = 100,
): Promise<GeneratedVisualAssetDto[]> {
  return apiJson<GeneratedVisualAssetDto[]>(
    `/generated-visual-assets?limit=${limit}`,
  );
}

export async function getImageGenerationReadiness(): Promise<ImageGenerationReadinessDto> {
  return apiJson("/generated-visual-assets/readiness");
}

export async function postIdentityReadiness(body: {
  reference_set_id?: string | null;
  primary_reference_id?: string | null;
  prompt?: string;
  consent?: boolean;
  paid_approval_granted?: boolean;
}): Promise<IdentitySubsystemReadinessDto> {
  return apiJson("/identity-generation/readiness", {
    method: "POST",
    body: {
      reference_set_id: body.reference_set_id || null,
      primary_reference_id: body.primary_reference_id || null,
      prompt: body.prompt || "",
      consent: Boolean(body.consent),
      paid_approval_granted: Boolean(body.paid_approval_granted),
    },
  });
}

export async function reviewGeneratedVisual(
  assetId: string,
  body: {
    identity_similarity?: string | null;
    brand_similarity?: string | null;
    user_accepted?: boolean | null;
    review_notes?: string | null;
  },
): Promise<GeneratedVisualAssetDto> {
  return apiJson(`/generated-visual-assets/${assetId}/review`, {
    method: "POST",
    body,
  });
}
