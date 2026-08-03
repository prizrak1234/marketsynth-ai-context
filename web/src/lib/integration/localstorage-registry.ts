/**
 * Product Alpha localStorage ownership registry (I1 — do not delete keys).
 */

export type StorageOwnership =
  | "mock_only"
  | "draft_only"
  | "future_backend_replacement"
  | "safe_preserve_during_integration"
  | "migration_required"
  | "eventual_removal";

export type StorageKeyEntry = {
  keyPattern: string;
  phase: string;
  ownership: StorageOwnership[];
  notes: string;
};

export const LOCALSTORAGE_REGISTRY: readonly StorageKeyEntry[] = [
  {
    keyPattern: "marketsynth.product_alpha.intake_draft.v1",
    phase: "A2/I2/P0.1",
    ownership: ["draft_only", "future_backend_replacement", "safe_preserve_during_integration"],
    notes:
      "P0.1: full draft local; explicit ProjectBrief sync; no auto-upload; local preserved after backend save",
  },
  {
    keyPattern: "marketsynth.product_alpha.intake_draft.by_project.v1.{projectId}",
    phase: "I2/P0.1",
    ownership: ["draft_only", "future_backend_replacement", "safe_preserve_during_integration"],
    notes: "Linked copy after Project create; briefSync metadata may point at ProjectBrief",
  },
  {
    keyPattern: "marketsynth.product_alpha.mock_projects.v1",
    phase: "A2",
    ownership: ["mock_only", "eventual_removal", "safe_preserve_during_integration"],
    notes: "Demo list; Workspace uses MOCK_PROJECTS / API in I1",
  },
  {
    keyPattern: "marketsynth.product_alpha.investigation.v1.{projectId}",
    phase: "A3",
    ownership: ["draft_only", "future_backend_replacement", "safe_preserve_during_integration"],
    notes: "Additive Investigation entity later",
  },
  {
    keyPattern: "marketsynth.product_alpha.verdict.v1.{projectId}",
    phase: "A4/I4",
    ownership: ["draft_only", "future_backend_replacement", "safe_preserve_during_integration"],
    notes:
      "I4 Option C SoT for commercial verdict preview; no auto-upload; not evidence-verified backend authority",
  },
  {
    keyPattern: "marketsynth.product_alpha.strategy.v1.{projectId}",
    phase: "A5/I5",
    ownership: ["draft_only", "future_backend_replacement", "safe_preserve_during_integration"],
    notes:
      "I5 Option B: local Strategy SoT (labelled); MarketingPlan is separate ops spine — no auto dual-write",
  },
  {
    keyPattern: "marketsynth.product_alpha.implementation_plan.v1.{projectId}",
    phase: "A6/I6",
    ownership: ["draft_only", "future_backend_replacement", "migration_required", "safe_preserve_during_integration"],
    notes:
      "I6 Option B: local ImplementationPlan SoT until dedicated domain. Link to MarketingPlan via FE metadata only; no auto-upload; write conversion blocked",
  },
  {
    keyPattern: "marketsynth.product_alpha.execution_package.v1.{projectId}",
    phase: "A7 parked",
    ownership: ["mock_only", "safe_preserve_during_integration"],
    notes: "A7 paused — do not treat as SoT",
  },
  {
    keyPattern: "marketsynth.integration.mode.v1",
    phase: "I1",
    ownership: ["safe_preserve_during_integration"],
    notes: "Integration mode override (mock|backend|hybrid)",
  },
] as const;
