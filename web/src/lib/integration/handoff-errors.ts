/**
 * I6 — Handoff / Implementation Plan errors.
 */

import { ApiError } from "@/lib/api/errors";

export type HandoffErrorKind =
  | "implementation_plan_not_available"
  | "marketing_plan_not_found"
  | "approved_plan_immutable"
  | "mapping_conflict"
  | "unsupported_task_mapping"
  | "unsupported_role"
  | "dependency_loss"
  | "acceptance_criteria_loss"
  | "stale_mapping"
  | "version_conflict"
  | "project_not_found"
  | "unauthorized"
  | "forbidden"
  | "approval_required"
  | "execution_boundary_violation"
  | "backend_unavailable"
  | "write_blocked"
  | "unknown_error";

export type HandoffError = {
  kind: HandoffErrorKind;
  message: string;
  status: number | null;
  actionHint: string;
};

export function normalizeHandoffError(err: unknown): HandoffError {
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return {
        kind: "unauthorized",
        message: "Требуется авторизация.",
        status: 401,
        actionHint: "Укажите API key.",
      };
    }
    if (err.status === 403) {
      return {
        kind: "forbidden",
        message: "Нет доступа.",
        status: 403,
        actionHint: "Вернитесь в Workspace.",
      };
    }
    if (err.status === 404) {
      return {
        kind: "marketing_plan_not_found",
        message: "MarketingPlan не найден.",
        status: 404,
        actionHint: "Related ops plan отсутствует — это нормально для I6 read-only.",
      };
    }
    if (err.status >= 500) {
      return {
        kind: "backend_unavailable",
        message: "Backend недоступен.",
        status: err.status,
        actionHint: "Не подставляем mock Implementation Plan как backend success.",
      };
    }
  }
  if (err instanceof TypeError) {
    return {
      kind: "backend_unavailable",
      message: "Сеть недоступна.",
      status: null,
      actionHint: "Backend mode: empty/error.",
    };
  }
  return {
    kind: "unknown_error",
    message: "Ошибка handoff.",
    status: null,
    actionHint: "Обновите страницу.",
  };
}

export function writeBlockedNoCreateApi(): HandoffError {
  return {
    kind: "write_blocked",
    message:
      "Local I6 preview remains non-writing. Durable MarketingPlan draft requires P1.2 handoff confirm.",
    status: null,
    actionHint:
      "Backend/hybrid: use «Проверить готовность» → explicit checkbox → «Создать черновик MarketingPlan».",
  };
}

export function executionBoundaryViolation(detail: string): HandoffError {
  return {
    kind: "execution_boundary_violation",
    message: detail,
    status: null,
    actionHint: "Не вызывать execution-runs / provider / publication из Implementation Plan.",
  };
}
