/**
 * P1.1 — ImplementationPlan error normalization.
 */

import { ApiError } from "@/lib/api/errors";

export type ImplementationPlanErrorKind =
  | "implementation_plan_not_found"
  | "strategy_not_approved"
  | "strategy_superseded"
  | "strategy_version_mismatch"
  | "immutable_plan"
  | "dependency_cycle"
  | "missing_acceptance_criteria"
  | "unauthorized"
  | "backend_unavailable"
  | "marketing_plan_boundary_violation"
  | "unknown_error";

export type ImplementationPlanError = {
  kind: ImplementationPlanErrorKind;
  message: string;
  status: number | null;
  actionHint: string;
};

export function normalizeImplementationPlanError(err: unknown): ImplementationPlanError {
  if (err instanceof ApiError) {
    const detail = String(
      (err.body as { safe_message?: string; detail?: string } | null)?.safe_message ||
        (err.body as { detail?: string } | null)?.detail ||
        err.message ||
        "",
    );
    if (err.status === 401) {
      return {
        kind: "unauthorized",
        message: "Требуется авторизация.",
        status: 401,
        actionHint: "Проверьте API key.",
      };
    }
    if (detail.includes("strategy_not_approved")) {
      return {
        kind: "strategy_not_approved",
        message: "ImplementationPlan требует approved MarketingStrategy.",
        status: err.status,
        actionHint: "Утвердите Strategy.",
      };
    }
    if (detail.includes("immutable_plan")) {
      return {
        kind: "immutable_plan",
        message: "Утверждённый ImplementationPlan неизменяем.",
        status: err.status,
        actionHint: "Создайте новую версию через supersede.",
      };
    }
    if (err.status === 404) {
      return {
        kind: "implementation_plan_not_found",
        message: "ImplementationPlan не найден.",
        status: 404,
        actionHint: "Backend mode: empty без mock fallback.",
      };
    }
    return {
      kind: "unknown_error",
      message: detail || "Ошибка ImplementationPlan API.",
      status: err.status,
      actionHint: "Backend mode: empty/error без mock fallback.",
    };
  }
  return {
    kind: "backend_unavailable",
    message: "Backend недоступен.",
    status: null,
    actionHint: "Не подменять mock-успехом.",
  };
}
