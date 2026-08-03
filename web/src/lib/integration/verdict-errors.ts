/**
 * I4 — Business Verdict errors.
 * Never convert backend failure into mock verdict success in backend mode.
 */

import { ApiError } from "@/lib/api/errors";

export type VerdictErrorKind =
  | "verdict_not_found"
  | "project_not_found"
  | "unauthorized"
  | "forbidden"
  | "invalid_transition"
  | "stale_version"
  | "snapshot_mismatch"
  | "insufficient_evidence"
  | "local_backend_conflict"
  | "approval_required"
  | "backend_unavailable"
  | "unsupported_capability"
  | "unknown_error";

export type VerdictError = {
  kind: VerdictErrorKind;
  message: string;
  status: number | null;
  actionHint: string;
};

export function normalizeVerdictError(err: unknown): VerdictError {
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
        message: "Нет доступа к вердикту проекта.",
        status: 403,
        actionHint: "Вернитесь в Workspace.",
      };
    }
    if (err.status === 404) {
      return {
        kind: "verdict_not_found",
        message: "Вердикт не найден на backend.",
        status: 404,
        actionHint: "В I4 backend BusinessVerdict API отсутствует — используйте local preview (hybrid).",
      };
    }
    if (err.status >= 500) {
      return {
        kind: "backend_unavailable",
        message: "Backend недоступен.",
        status: err.status,
        actionHint: "Не подставляем mock verdict в backend mode.",
      };
    }
  }
  if (err instanceof TypeError) {
    return {
      kind: "backend_unavailable",
      message: "Сеть недоступна.",
      status: null,
      actionHint: "Backend mode: empty/error — без mock fallback.",
    };
  }
  return {
    kind: "unknown_error",
    message: "Ошибка загрузки вердикта.",
    status: null,
    actionHint: "Обновите страницу.",
  };
}

export function unsupportedVerdictCapability(): VerdictError {
  return {
    kind: "unsupported_capability",
    message:
      "Durable BusinessVerdict domain не реализован (I4 Option C). Evidence SoT отсутствует.",
    status: null,
    actionHint:
      "Локальный предварительный вердикт доступен в mock/hybrid. Не утверждайте его как evidence-verified backend.",
  };
}

export function insufficientEvidenceError(): VerdictError {
  return {
    kind: "insufficient_evidence",
    message: "Недостаточно durable evidence для evidence-verified Business Verdict.",
    status: null,
    actionHint: "Вернитесь в Investigation или используйте только local preview с явной меткой.",
  };
}
