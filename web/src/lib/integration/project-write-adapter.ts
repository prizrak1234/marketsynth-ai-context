/**
 * I2 Project write adapter — maps errors + soft validation for Project API.
 * No backend domain logic; thin client-side normalization only.
 */

import { ApiError } from "@/lib/api/errors";

export type ProjectWriteErrorKind =
  | "validation_error"
  | "unauthorized"
  | "forbidden"
  | "project_not_found"
  | "conflict"
  | "network_error"
  | "backend_unavailable"
  | "ambiguous_create_result"
  | "unsupported_mapping"
  | "unknown_error";

export type ProjectWriteError = {
  kind: ProjectWriteErrorKind;
  message: string;
  status: number | null;
  actionHint: string;
};

export function normalizeProjectWriteError(err: unknown): ProjectWriteError {
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return {
        kind: "unauthorized",
        message: "Требуется авторизация.",
        status: 401,
        actionHint: "Войдите снова (API key) и повторите.",
      };
    }
    if (err.status === 403) {
      return {
        kind: "forbidden",
        message: "Нет доступа к этому проекту.",
        status: 403,
        actionHint: "Вернитесь в Workspace или выберите свой проект.",
      };
    }
    if (err.status === 404) {
      return {
        kind: "project_not_found",
        message: "Проект не найден на backend.",
        status: 404,
        actionHint: "Не создавайте дубликат автоматически — сверьтесь с Workspace.",
      };
    }
    if (err.status === 409) {
      return {
        kind: "conflict",
        message: "Конфликт при сохранении проекта.",
        status: 409,
        actionHint: "Обновите данные и сохраните снова.",
      };
    }
    if (err.status === 422 || err.status === 400) {
      return {
        kind: "validation_error",
        message: err.message || "Ошибка валидации Project API.",
        status: err.status,
        actionHint: "Исправьте название/описание и повторите.",
      };
    }
    if (err.status >= 500) {
      return {
        kind: "backend_unavailable",
        message: "Backend временно недоступен.",
        status: err.status,
        actionHint: "Черновик сохранён локально. Повторите позже.",
      };
    }
    return {
      kind: "unknown_error",
      message: err.message || "Неизвестная ошибка API.",
      status: err.status,
      actionHint: "Черновик сохранён. Вернитесь в Workspace или повторите.",
    };
  }

  if (err instanceof TypeError) {
    return {
      kind: "network_error",
      message: "Сеть недоступна или ответ потерян.",
      status: null,
      actionHint:
        "Не создавайте проект повторно автоматически — обновите Workspace и при необходимости сверьте.",
    };
  }

  return {
    kind: "unknown_error",
    message: "Не удалось сохранить проект.",
    status: null,
    actionHint: "Черновик сохранён локально.",
  };
}

export function ambiguousCreateError(): ProjectWriteError {
  return {
    kind: "ambiguous_create_result",
    message:
      "Запрос на создание мог дойти до сервера, но ответ не получен. Повторный POST заблокирован.",
    status: null,
    actionHint:
      "Откройте Workspace, найдите проект или используйте «Сверить», не создавайте второй.",
  };
}
