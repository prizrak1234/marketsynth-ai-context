/** VS.2B — Video Studio capabilities + parameter preview API. */

import { apiJson } from "@/lib/api/client";

export type VideoAspectRatioOptionDto = {
  id: string;
  label_ru: string;
  label_en: string;
  purpose_ru: string;
  availability: "available" | "post_process" | "unavailable";
  disabled_reason_ru: string | null;
};

export type CameraMovementOptionDto = {
  id: string;
  label_ru: string;
  label_en: string;
  description_ru: string;
  provisional: boolean;
};

export type VideoStudioCapabilitiesDto = {
  requested_durations_seconds: number[];
  provider_supported_single_clip_durations_seconds: number[];
  single_clip_max_seconds: number;
  single_clip_min_seconds: number;
  target_scene_duration_seconds: number;
  aspect_ratios: VideoAspectRatioOptionDto[];
  camera_movements: CameraMovementOptionDto[];
  camera_movements_catalog_status: string;
  camera_movements_catalog_note_ru: string;
  long_form_planning_available: boolean;
  long_form_generation_available: boolean;
  start_end_frame_available: boolean;
  single_clip_generation_available: boolean;
  assembly_pipeline_ready: boolean;
};

export type VideoStudioPreviewDto = {
  duration_mode: "single_clip" | "long_form";
  requested_duration_seconds: number;
  aspect_ratio: string;
  source_mode: string;
  camera_movement_id: string;
  scene_description: string;
  scene_count: number;
  scene_durations_seconds: number[];
  estimated_provider_calls: number;
  estimated_cost_label: string;
  estimated_wait_seconds: number;
  what_will_be_created_ru: string;
  limitations_ru: string[];
  generation_available: boolean;
  plan_only: boolean;
  primary_action_ru: string;
  blocked_reason_ru: string | null;
  approval_required: boolean;
  readiness_message_ru: string;
  normalized_motion_prompt?: string | null;
};

export async function fetchVideoStudioCapabilities(): Promise<VideoStudioCapabilitiesDto> {
  return apiJson<VideoStudioCapabilitiesDto>("/media-generation/video-studio/capabilities");
}

export async function previewVideoStudioParameters(body: {
  requested_duration_seconds: number;
  aspect_ratio: string;
  source_mode: "no_start_frame" | "image" | "start_end_frame";
  start_asset_id?: string | null;
  end_asset_id?: string | null;
  camera_movement_id: string;
  camera_movement_instruction?: string | null;
  scene_description: string;
}): Promise<VideoStudioPreviewDto> {
  return apiJson<VideoStudioPreviewDto>("/media-generation/video-studio/preview", {
    method: "POST",
    body,
  });
}

export function isLongFormDuration(
  seconds: number,
  singleClipMaxSeconds = 15,
): boolean {
  return seconds > singleClipMaxSeconds;
}
