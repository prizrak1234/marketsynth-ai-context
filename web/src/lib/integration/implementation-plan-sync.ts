/**
 * P1.1 — local ImplementationPlan migration boundary.
 * Key: marketsynth.product_alpha.implementation_plan.v1.{projectId}
 */

export const LOCAL_IMPLEMENTATION_PLAN_KEY_PREFIX =
  "marketsynth.product_alpha.implementation_plan.v1.";

export function localImplementationPlanStorageKey(projectId: string): string {
  return `${LOCAL_IMPLEMENTATION_PLAN_KEY_PREFIX}${projectId}`;
}

export function localImplementationPlanImportPolicy() {
  return {
    autoUpload: false as const,
    requiresExplicitAction: true as const,
    statusAfterImport: "draft" as const,
    originAfterImport: "imported_local_preview" as const,
    requiresApprovedStrategy: true as const,
    createsMarketingPlan: false as const,
    createsSpecialistTasks: false as const,
    backendApprovedAuthoritative: true as const,
  };
}
