"use client";

import type { ContentFactoryProductChannelId } from "@/lib/content-factory/labels";
import { isRecoveryPreviewRole } from "@/lib/home/recovery-preview";

export const OWNER_PREVIEW_QUERY_KEY = "owner_preview";
export const OWNER_PREVIEW_CONTENT_FACTORY = "content_factory";

export type ContentFactoryBriefSeed = {
  channel?: ContentFactoryProductChannelId;
  topic?: string;
  goal?: string;
  audience?: string;
  period?: string;
  frequency?: string;
  format?: string;
  sourceMaterials?: string;
};

export function isOwnerContentFactoryPreviewParam(
  value: string | null | undefined,
): boolean {
  return value === OWNER_PREVIEW_CONTENT_FACTORY;
}

export function canAccessOwnerContentFactoryPreview(role: string | null | undefined): boolean {
  return isRecoveryPreviewRole(role);
}

/** Owner-only canonical workspace URL — not recovery-preview. */
export function workspaceOwnerContentFactoryPreviewUrl(projectId?: string | null): string {
  const params = new URLSearchParams({
    [OWNER_PREVIEW_QUERY_KEY]: OWNER_PREVIEW_CONTENT_FACTORY,
  });
  if (projectId) {
    params.set("project_id", projectId);
  }
  return `/workspace?${params.toString()}`;
}

export function parseOwnerContentFactoryPreview(searchParams: URLSearchParams): {
  active: boolean;
  projectId: string | null;
} {
  return {
    active: isOwnerContentFactoryPreviewParam(searchParams.get(OWNER_PREVIEW_QUERY_KEY)),
    projectId: searchParams.get("project_id"),
  };
}
