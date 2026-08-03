/**
 * P0.5 — BusinessVerdict sync / local import boundary.
 *
 * Local key: marketsynth.product_alpha.verdict.v1.{projectId}
 * No auto-upload. Explicit conversion → draft only.
 */

export const LOCAL_VERDICT_KEY_PREFIX = "marketsynth.product_alpha.verdict.v1.";

export function localVerdictStorageKey(projectId: string): string {
  return `${LOCAL_VERDICT_KEY_PREFIX}${projectId}`;
}

export type LocalVerdictImportDecision = {
  autoUpload: false;
  requiresExplicitAction: true;
  statusAfterImport: "draft";
  originAfterImport: "deterministic_local_import";
  humanReviewRequired: true;
  backendApprovedAuthoritative: true;
};

export function localVerdictImportPolicy(): LocalVerdictImportDecision {
  return {
    autoUpload: false,
    requiresExplicitAction: true,
    statusAfterImport: "draft",
    originAfterImport: "deterministic_local_import",
    humanReviewRequired: true,
    backendApprovedAuthoritative: true,
  };
}

export function readLocalVerdictRaw(projectId: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(localVerdictStorageKey(projectId));
  } catch {
    return null;
  }
}
