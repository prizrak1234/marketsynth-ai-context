/**
 * P1.2 — MarketingPlan handoff error normalization.
 * Backend mode never falls back to mock success.
 */

import { ApiError } from "@/lib/api/errors";

export type MarketingPlanHandoffErrorKind =
  | "implementation_plan_not_found"
  | "implementation_plan_not_approved"
  | "readiness_not_ready_for_handoff"
  | "stale_implementation_plan"
  | "preview_stale"
  | "fingerprint_mismatch"
  | "explicit_confirmation_required"
  | "existing_marketing_plan_conflict"
  | "duplicate_handoff"
  | "marketing_plan_create_unsafe"
  | "unauthorized"
  | "forbidden"
  | "backend_unavailable"
  | "execution_firewall_violation"
  | "unknown_error";

export type MarketingPlanHandoffError = {
  kind: MarketingPlanHandoffErrorKind;
  message: string;
  status: number | null;
  actionHint: string;
};

const DETAIL_MAP: Array<{ needle: string; kind: MarketingPlanHandoffErrorKind; hint: string }> = [
  {
    needle: "explicit_confirmation",
    kind: "explicit_confirmation_required",
    hint: "Отметьте подтверждение создания только черновика.",
  },
  {
    needle: "fingerprint_mismatch",
    kind: "fingerprint_mismatch",
    hint: "Обновите preview — fingerprint изменился.",
  },
  {
    needle: "preview_stale",
    kind: "preview_stale",
    hint: "Сформируйте новый preview.",
  },
  {
    needle: "stale_implementation_plan",
    kind: "stale_implementation_plan",
    hint: "ImplementationPlan версия устарела.",
  },
  {
    needle: "implementation_plan_not_approved",
    kind: "implementation_plan_not_approved",
    hint: "Сначала утвердите ImplementationPlan.",
  },
  {
    needle: "readiness_not_ready_for_handoff",
    kind: "readiness_not_ready_for_handoff",
    hint: "Доведите readiness до ready_for_handoff.",
  },
  {
    needle: "existing_marketing_plan_conflict",
    kind: "existing_marketing_plan_conflict",
    hint: "Выберите политику create_new_draft или отмените.",
  },
  {
    needle: "marketing_plan_create_unsafe",
    kind: "marketing_plan_create_unsafe",
    hint: "Draft create заблокирован.",
  },
];

export function normalizeMarketingPlanHandoffError(err: unknown): MarketingPlanHandoffError {
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
        message: "Нет доступа к проекту.",
        status: 403,
        actionHint: "Вернитесь в Workspace.",
      };
    }
    if (err.status >= 500) {
      return {
        kind: "backend_unavailable",
        message: "Backend недоступен.",
        status: err.status,
        actionHint: "Mock success не подставляется.",
      };
    }
    const detail = String(
      (err.body as { safe_message?: string; detail?: string } | null)?.safe_message ||
        (err.body as { detail?: string } | null)?.detail ||
        err.message ||
        "",
    );
    for (const row of DETAIL_MAP) {
      if (detail.includes(row.needle)) {
        return {
          kind: row.kind,
          message: detail,
          status: err.status,
          actionHint: row.hint,
        };
      }
    }
    return {
      kind: "unknown_error",
      message: detail || "Ошибка handoff.",
      status: err.status,
      actionHint: "Проверьте preview и eligibility.",
    };
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
    actionHint: "Повторите preview.",
  };
}
