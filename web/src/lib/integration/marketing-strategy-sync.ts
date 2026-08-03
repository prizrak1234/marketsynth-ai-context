/**
 * P0.6 — local Strategy migration boundary.
 * Key: marketsynth.product_alpha.strategy.v1.{projectId}
 */

export const LOCAL_STRATEGY_KEY_PREFIX = "marketsynth.product_alpha.strategy.v1.";

export function localStrategyStorageKey(projectId: string): string {
  return `${LOCAL_STRATEGY_KEY_PREFIX}${projectId}`;
}

export function localStrategyImportPolicy() {
  return {
    autoUpload: false as const,
    requiresExplicitAction: true as const,
    statusAfterImport: "draft" as const,
    originAfterImport: "imported_local_preview" as const,
    requiresApprovedVerdict: true as const,
    createsMarketingPlan: false as const,
    backendApprovedAuthoritative: true as const,
  };
}
