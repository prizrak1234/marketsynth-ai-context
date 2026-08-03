"use client";

import { isRecoveryPreviewRole } from "@/lib/home/recovery-preview";

export const OWNER_PREVIEW_QUERY_KEY = "owner_preview";
export const OWNER_PREVIEW_VIDEO = "video";

export function isOwnerVideoPreviewParam(value: string | null | undefined): boolean {
  return value === OWNER_PREVIEW_VIDEO;
}

export function canAccessOwnerVideoPreview(role: string | null | undefined): boolean {
  return isRecoveryPreviewRole(role);
}

export function workspaceOwnerVideoPreviewUrl(): string {
  const params = new URLSearchParams({
    [OWNER_PREVIEW_QUERY_KEY]: OWNER_PREVIEW_VIDEO,
  });
  return `/workspace?${params.toString()}`;
}

export function parseOwnerVideoPreview(searchParams: URLSearchParams): { active: boolean } {
  return {
    active: isOwnerVideoPreviewParam(searchParams.get(OWNER_PREVIEW_QUERY_KEY)),
  };
}
