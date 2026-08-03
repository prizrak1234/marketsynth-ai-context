/**
 * Map ProductIntakeDraft → existing Project create/update payloads.
 * Only name + description are persisted. Full draft stays local.
 */

import type { ProjectCreateRequest, ProjectUpdateRequest } from "@/lib/api/endpoints/projects";
import type { ProjectIntakeDraft } from "@/lib/project-intake/types";

const DESCRIPTION_MAX = 4000;

export const PERSISTED_INTAKE_FIELDS = [
  "projectBasics.name → Project.name",
  "projectBasics.ideaDescription (+ short product hint) → Project.description",
] as const;

export const LOCAL_ONLY_INTAKE_SECTIONS = [
  "product (except short hint in description)",
  "market",
  "audience",
  "economics",
  "materials / attachments",
  "assumptions",
  "missingData",
  "readiness",
] as const;

/** Lightweight pointer in Project.config — not the full brief. */
export type MarketsynthProjectConfigPointer = {
  localDraftId: string;
  submissionFingerprint: string;
  localDraftVersion: string;
};

export function buildProjectDescription(draft: ProjectIntakeDraft): string {
  const idea = draft.projectBasics.ideaDescription.trim();
  const sold = draft.product.whatIsSold.trim();
  const value = draft.product.valueProposition.trim();
  const parts: string[] = [];
  if (idea) parts.push(idea);
  if (sold) parts.push(`Product: ${sold}`);
  if (value) parts.push(`Value: ${value}`);
  const text = parts.join("\n\n").trim() || "Marketsynth intake project";
  return text.length > DESCRIPTION_MAX ? `${text.slice(0, DESCRIPTION_MAX - 1)}…` : text;
}

export function buildProjectName(draft: ProjectIntakeDraft): string {
  const name = draft.projectBasics.name.trim();
  return name || "Untitled project";
}

/** Fingerprint of persistable core — for duplicate-submit detection. */
export function buildSubmissionFingerprint(draft: ProjectIntakeDraft): string {
  const payload = JSON.stringify({
    draftId: draft.id,
    name: buildProjectName(draft),
    description: buildProjectDescription(draft),
  });
  let hash = 0;
  for (let i = 0; i < payload.length; i++) {
    hash = (hash * 31 + payload.charCodeAt(i)) | 0;
  }
  return `fp_${draft.id}_${(hash >>> 0).toString(16)}`;
}

export function mapIntakeToProjectCreate(draft: ProjectIntakeDraft): ProjectCreateRequest {
  return {
    name: buildProjectName(draft),
    description: buildProjectDescription(draft),
  };
}

export function mapIntakeToProjectUpdate(
  draft: ProjectIntakeDraft,
  fingerprint: string,
  existingConfig?: Record<string, unknown> | null,
): ProjectUpdateRequest {
  const pointer: MarketsynthProjectConfigPointer = {
    localDraftId: draft.id,
    submissionFingerprint: fingerprint,
    localDraftVersion: draft.updatedAt,
  };
  return {
    name: buildProjectName(draft),
    description: buildProjectDescription(draft),
    config: {
      ...(existingConfig && typeof existingConfig === "object" ? existingConfig : {}),
      marketsynth_i2: pointer,
    },
  };
}

export function readConfigPointer(
  config: Record<string, unknown> | undefined | null,
): MarketsynthProjectConfigPointer | null {
  if (!config || typeof config !== "object") return null;
  const raw = config.marketsynth_i2;
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  if (
    typeof o.localDraftId !== "string" ||
    typeof o.submissionFingerprint !== "string" ||
    typeof o.localDraftVersion !== "string"
  ) {
    return null;
  }
  return {
    localDraftId: o.localDraftId,
    submissionFingerprint: o.submissionFingerprint,
    localDraftVersion: o.localDraftVersion,
  };
}
