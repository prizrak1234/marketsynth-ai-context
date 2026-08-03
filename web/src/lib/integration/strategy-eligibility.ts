/**
 * I4 — Strategy eligibility from Business Verdict (frontend contract).
 * Does not call Strategy backend. Does not create execution approvals.
 */

import type { VerdictOriginMeta } from "@/lib/integration/verdict-origin";
import type { BusinessVerdictType, VerdictStatus } from "@/lib/verdict/types";
import type { VerdictReadinessStatus } from "@/lib/investigation/types";

export type StrategyEligibilityResult = {
  allow: boolean;
  mode: "go" | "conditional_go" | "blocked" | "preview_only";
  redirect: "strategy" | "investigation" | "pivot" | "none";
  reason: string;
  requiresVisibleConditions: boolean;
  createsExecutionApproval: false;
  generatesStrategyBackend: false;
};

export function resolveStrategyEligibility(input: {
  verdictType: BusinessVerdictType | null;
  verdictStatus: VerdictStatus | null;
  origin: VerdictOriginMeta | null;
  /** Investigation readiness — must NOT equal verdict type */
  readinessStatus?: VerdictReadinessStatus | null;
}): StrategyEligibilityResult {
  const baseDenied = {
    createsExecutionApproval: false as const,
    generatesStrategyBackend: false as const,
  };

  if (!input.verdictType || !input.verdictStatus) {
    return {
      ...baseDenied,
      allow: false,
      mode: "blocked",
      redirect: "investigation",
      reason: "Нет Business Verdict.",
      requiresVisibleConditions: false,
    };
  }

  // Ready-for-review never implies GO
  if (input.readinessStatus === "ready_for_review" && !input.verdictType) {
    return {
      ...baseDenied,
      allow: false,
      mode: "blocked",
      redirect: "none",
      reason: "ready_for_review ≠ GO — вердикт ещё не создан.",
      requiresVisibleConditions: false,
    };
  }

  if (input.verdictStatus === "draft" || input.verdictStatus === "under_review") {
    return {
      ...baseDenied,
      allow: false,
      mode: "preview_only",
      redirect: "none",
      reason: "Draft / under_review — Strategy generation blocked (preview only).",
      requiresVisibleConditions: input.verdictType === "CONDITIONAL_GO",
    };
  }

  if (input.verdictStatus === "superseded") {
    return {
      ...baseDenied,
      allow: false,
      mode: "blocked",
      redirect: "none",
      reason: "Superseded verdict cannot unlock Strategy.",
      requiresVisibleConditions: false,
    };
  }

  // approved local/mock: Alpha UI may open strategy route; never claim backend strategy create
  if (input.verdictType === "GO") {
    return {
      ...baseDenied,
      allow: true,
      mode: "go",
      redirect: "strategy",
      reason: "Approved GO — eligible for Strategy (frontend). Backend Strategy API не вызывается в I4.",
      requiresVisibleConditions: false,
    };
  }

  if (input.verdictType === "CONDITIONAL_GO") {
    return {
      ...baseDenied,
      allow: true,
      mode: "conditional_go",
      redirect: "strategy",
      reason:
        "Approved CONDITIONAL_GO — Strategy allowed with mandatory visible conditions. No execution approval.",
      requiresVisibleConditions: true,
    };
  }

  if (input.verdictType === "NO_GO") {
    return {
      ...baseDenied,
      allow: false,
      mode: "blocked",
      redirect: "pivot",
      reason: "NO_GO — Strategy blocked; Pivot path allowed.",
      requiresVisibleConditions: false,
    };
  }

  // INSUFFICIENT_DATA
  return {
    ...baseDenied,
    allow: false,
    mode: "blocked",
    redirect: "investigation",
    reason: "INSUFFICIENT_DATA — Strategy blocked; return to Investigation.",
    requiresVisibleConditions: false,
  };
}

/** Readiness must never coerce into BusinessVerdictType. */
export function readinessImpliesVerdictType(
  readiness: VerdictReadinessStatus,
): BusinessVerdictType | null {
  void readiness;
  return null;
}

/** Verdict review approval must never create execution approval. */
export function verdictApprovalCreatesExecutionApproval(): false {
  return false;
}
