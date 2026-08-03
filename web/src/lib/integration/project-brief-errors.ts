/**
 * P0.1 — ProjectBrief integration errors.
 */

import { ApiError } from "@/lib/api/errors";

export type ProjectBriefErrorKind =
  | "project_not_found"
  | "brief_not_found"
  | "unauthorized"
  | "forbidden"
  | "validation_error"
  | "invalid_transition"
  | "stale_version"
  | "fingerprint_conflict"
  | "duplicate_submission"
  | "backend_unavailable"
  | "network_error"
  | "migration_blocked"
  | "project_required"
  | "unknown_error";

export type ProjectBriefError = {
  kind: ProjectBriefErrorKind;
  message: string;
  status: number | null;
  actionHint: string;
};

export function normalizeProjectBriefError(err: unknown): ProjectBriefError {
  if (err instanceof ApiError) {
    const detail = typeof err.body === "object" && err.body && "detail" in err.body
      ? String((err.body as { detail?: unknown }).detail ?? "")
      : "";
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
        actionHint: "Проверьте владельца Project.",
      };
    }
    if (err.status === 404) {
      return {
        kind: detail.toLowerCase().includes("brief") ? "brief_not_found" : "project_not_found",
        message: detail || "Не найдено.",
        status: 404,
        actionHint: "Создайте Project или сохраните бриф заново.",
      };
    }
    if (err.status === 409) {
      if (detail.includes("duplicate_fingerprint")) {
        return {
          kind: "duplicate_submission",
          message: "Такой бриф уже submitted.",
          status: 409,
          actionHint: "Создайте новую версию через supersede или измените содержание.",
        };
      }
      if (detail.includes("immutable") || detail.includes("invalid_transition")) {
        return {
          kind: "invalid_transition",
          message: "Недопустимый переход статуса брифа.",
          status: 409,
          actionHint: "Submitted brief immutable — создайте новую версию.",
        };
      }
      return {
        kind: "fingerprint_conflict",
        message: detail || "Конфликт версии брифа.",
        status: 409,
        actionHint: "Обновите данные и повторите явно.",
      };
    }
    if (err.status === 422) {
      return {
        kind: "validation_error",
        message: "Ошибка валидации брифа.",
        status: 422,
        actionHint: "Проверьте обязательные поля.",
      };
    }
    if (err.status >= 500) {
      return {
        kind: "backend_unavailable",
        message: "Backend недоступен.",
        status: err.status,
        actionHint: "Backend mode: не подставляем mock success.",
      };
    }
  }
  if (err instanceof TypeError) {
    return {
      kind: "network_error",
      message: "Сеть недоступна.",
      status: null,
      actionHint: "Проверьте соединение.",
    };
  }
  return {
    kind: "unknown_error",
    message: "Ошибка сохранения брифа.",
    status: null,
    actionHint: "Черновик остаётся локально.",
  };
}
