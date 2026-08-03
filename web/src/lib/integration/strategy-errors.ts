/**
 * I5 — Strategy / MarketingPlan errors.
 * Never convert plan API failure into successful Strategy.
 */

import { ApiError } from "@/lib/api/errors";

export type StrategyErrorKind =
  | "strategy_not_available"
  | "marketing_plan_not_found"
  | "project_not_found"
  | "campaign_not_found"
  | "unauthorized"
  | "forbidden"
  | "semantic_conflict"
  | "version_conflict"
  | "unsupported_mapping"
  | "local_backend_conflict"
  | "invalid_strategy_eligibility"
  | "backend_unavailable"
  | "unknown_error";

export type StrategyError = {
  kind: StrategyErrorKind;
  message: string;
  status: number | null;
  actionHint: string;
};

export function normalizeStrategyError(err: unknown): StrategyError {
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
        message: "Нет доступа к MarketingPlan.",
        status: 403,
        actionHint: "Вернитесь в Workspace.",
      };
    }
    if (err.status === 404) {
      return {
        kind: "marketing_plan_not_found",
        message: "MarketingPlan не найден.",
        status: 404,
        actionHint: "Plan отсутствует — это не равно Strategy.",
      };
    }
    if (err.status >= 500) {
      return {
        kind: "backend_unavailable",
        message: "Backend недоступен.",
        status: err.status,
        actionHint: "Не подставляем local Strategy как backend success.",
      };
    }
  }
  if (err instanceof TypeError) {
    return {
      kind: "backend_unavailable",
      message: "Сеть недоступна.",
      status: null,
      actionHint: "Backend mode: empty/error без mock fallback.",
    };
  }
  return {
    kind: "unknown_error",
    message: "Ошибка Strategy / MarketingPlan integration.",
    status: null,
    actionHint: "Обновите страницу.",
  };
}

export function invalidEligibilityError(reason: string): StrategyError {
  return {
    kind: "invalid_strategy_eligibility",
    message: reason,
    status: null,
    actionHint: "Соблюдайте I4 Verdict eligibility. MarketingPlan не обходит Verdict.",
  };
}

export function semanticConflictPlanIsNotStrategy(): StrategyError {
  return {
    kind: "semantic_conflict",
    message:
      "MarketingPlan — operational execution spine, не MarketingStrategy. Не заявляем plan как Strategy SoT.",
    status: null,
    actionHint: "Смотрите ops-plan panel отдельно от strategic sections.",
  };
}
