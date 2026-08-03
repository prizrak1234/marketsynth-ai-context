/**
 * I3 — Investigation error normalization.
 * Never convert errors into fake research progress.
 */

import { ApiError } from "@/lib/api/errors";

export type InvestigationErrorKind =
  | "investigation_not_found"
  | "project_not_found"
  | "unauthorized"
  | "forbidden"
  | "invalid_state"
  | "stale_version"
  | "unsupported_capability"
  | "source_unavailable"
  | "evidence_conflict"
  | "backend_unavailable"
  | "network_error"
  | "partial_integration"
  | "unknown_error";

export type InvestigationError = {
  kind: InvestigationErrorKind;
  message: string;
  status: number | null;
  actionHint: string;
};

export function normalizeInvestigationError(err: unknown): InvestigationError {
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return {
        kind: "unauthorized",
        message: "Требуется авторизация.",
        status: 401,
        actionHint: "Укажите API key и обновите страницу.",
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
    if (err.status === 404) {
      return {
        kind: "project_not_found",
        message: "Проект не найден.",
        status: 404,
        actionHint: "Проверьте ID проекта в Workspace.",
      };
    }
    if (err.status >= 500) {
      return {
        kind: "backend_unavailable",
        message: "Backend временно недоступен.",
        status: err.status,
        actionHint: "Повторите позже. Mock-доказательства не подставляются.",
      };
    }
    return {
      kind: "unknown_error",
      message: err.message || "Ошибка Investigation API.",
      status: err.status,
      actionHint: "Черновик локального investigation сохранён, если был.",
    };
  }

  if (err instanceof TypeError) {
    return {
      kind: "network_error",
      message: "Сеть недоступна.",
      status: null,
      actionHint: "Проверьте соединение. Прогресс research не симулируется.",
    };
  }

  return {
    kind: "unknown_error",
    message: "Неизвестная ошибка Investigation.",
    status: null,
    actionHint: "Обновите страницу или вернитесь в Workspace.",
  };
}

export function unsupportedCapabilityError(capability: string): InvestigationError {
  return {
    kind: "unsupported_capability",
    message: `Возможность «${capability}» не представлена backend Investigation domain.`,
    status: null,
    actionHint: "Пока доступны только проекции существующих Project/Campaign/Skill данных.",
  };
}

export function partialIntegrationNotice(): InvestigationError {
  return {
    kind: "partial_integration",
    message:
      "Investigation Workspace частично интегрирован: Project/Campaign/Supervisor проекции доступны; Sources/Evidence — нет durable SoT.",
    status: null,
    actionHint: "Не трактуйте Supervisor Finding или LLM ответ как confirmed evidence.",
  };
}
