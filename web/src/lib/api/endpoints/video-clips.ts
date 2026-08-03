/** VS.2A commercial image→video clip API (entrepreneur-safe DTOs). */

import { apiJson } from "@/lib/api/client";

export type VideoClipPreviewDto = {
  clip_request_id: string;
  status: string;
  motion_brief: string;
  duration_seconds: number;
  aspect_ratio: string;
  estimated_cost_label: string;
  estimated_wait_seconds: number;
  what_will_be_created_ru: string;
  limitations_ru: string[];
  ready_to_generate: boolean;
  blocked_reason_ru: string | null;
  approval_required?: boolean;
};

export type VideoClipExecutionDto = {
  clip_request_id: string;
  status: string;
  user_message_ru: string;
  result_asset_id: string | null;
  result_playback_uri: string | null;
  requested_duration_seconds?: number | null;
  actual_duration_seconds?: number | null;
  duration_delta_seconds?: number | null;
  duration_validation_status?: "matched" | "within_tolerance" | "mismatch" | null;
  can_accept: boolean;
  can_retry_motion: boolean;
  can_create_variant: boolean;
  can_add_to_project: boolean;
  can_reconcile?: boolean;
  can_contact_admin?: boolean;
};

export type VideoClipHydrationDto = {
  clip_request_id: string;
  status: string;
  source_image_asset_id: string;
  preview: VideoClipPreviewDto | null;
  execution: VideoClipExecutionDto | null;
};

export type VideoOwnerAcceptancePreviewDto = {
  source_image_asset_id: string;
  clip_request_id: string;
  result_asset_id: string | null;
  user_request_id: string | null;
  seed_brief: string;
  source_user_accepted: boolean;
  video_user_accepted: boolean | null;
  execution: VideoClipExecutionDto;
};

export async function getVideoClipBySource(
  sourceImageAssetId: string,
): Promise<VideoClipHydrationDto | null> {
  const params = new URLSearchParams({ source_image_asset_id: sourceImageAssetId });
  return apiJson<VideoClipHydrationDto | null>(
    `/media-generation/video-clips?${params.toString()}`,
  );
}

export async function getOwnerVideoAcceptancePreview(): Promise<VideoOwnerAcceptancePreviewDto> {
  return apiJson<VideoOwnerAcceptancePreviewDto>(
    "/media-generation/video-clips/owner-acceptance-preview",
  );
}

export async function previewVideoClip(body: {
  source_image_asset_id: string;
  motion_brief: string;
  duration_seconds: number;
  aspect_ratio: string;
  camera_movement_id?: string | null;
  camera_movement_instruction?: string | null;
  project_id?: string | null;
  user_request_id?: string | null;
}): Promise<VideoClipPreviewDto> {
  return apiJson<VideoClipPreviewDto>("/media-generation/video-clips/preview", {
    method: "POST",
    body,
  });
}

export async function generateVideoClip(
  clipRequestId: string,
  idempotencyKey: string,
  approved = true,
): Promise<VideoClipExecutionDto> {
  return apiJson<VideoClipExecutionDto>(
    `/media-generation/video-clips/${clipRequestId}/generate`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: { approved },
    },
  );
}

export async function reconcileVideoClip(
  clipRequestId: string,
): Promise<VideoClipExecutionDto> {
  return apiJson<VideoClipExecutionDto>(
    `/media-generation/video-clips/${clipRequestId}/reconcile`,
    { method: "POST" },
  );
}
